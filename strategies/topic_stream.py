"""Strategy for generating a streamgraph of topic trends over time."""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from openai import OpenAI
from sklearn.cluster import KMeans

from .base import Strategy


class TopicStreamStrategy(Strategy):
    """Generate a streamgraph showing topic trends over time."""

    name = "topic_stream"
    description = "Streamgraph of how topics rise and fall over time"

    # Configuration options
    max_topics: int = 10  # Maximum number of topic clusters
    period_weeks: int = 2  # Aggregate into N-week periods

    def run(self) -> dict[str, Any]:
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            env_path = self.conversations_dir.parent / "0_time_series" / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            os.environ["OPENAI_API_KEY"] = api_key
                            break

        if not api_key:
            error_msg = "OPENAI_API_KEY not found"
            self.write_output(f"# Topic Stream\n\nError: {error_msg}")
            return {"error": error_msg}

        files = self.get_conversation_files()
        records: list[dict] = []

        print("Extracting conversations...")
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                first_msg = self._extract_first_user_message(data)
                if not first_msg or len(first_msg["text"].strip()) < 10:
                    continue

                # Use ISO week for weekly aggregation
                dt = datetime.fromtimestamp(first_msg["time"])
                iso_year, iso_week, _ = dt.isocalendar()
                # Group into N-week periods
                period_num = (iso_week - 1) // self.period_weeks
                period_key = f"{iso_year}-P{period_num:02d}"

                records.append({
                    "question": first_msg["text"],
                    "timestamp": first_msg["time"],
                    "period": period_key,
                })

            except Exception:
                pass

        if not records:
            self.write_output("# Topic Stream\n\nNo valid conversations found.")
            return {"error": "No valid conversations"}

        print(f"Processing {len(records)} conversations...")

        # Get embeddings
        client = OpenAI()
        batch_size = 100
        embeddings: list[list[float]] = []

        for start in range(0, len(records), batch_size):
            end = min(start + batch_size, len(records))
            batch = [r["question"][:1200] for r in records[start:end]]
            print(f"  Embedding batch {start}-{end}...")
            resp = client.embeddings.create(model="text-embedding-3-small", input=batch)
            ordered = sorted(resp.data, key=lambda d: d.index)
            embeddings.extend([item.embedding for item in ordered])

        X = np.array(embeddings)
        n = len(records)

        # Global clustering using configured max_topics
        k = min(self.max_topics, n // 50)  # At least 50 conversations per topic
        k = max(3, k)  # Minimum 3 topics

        print(f"Global clustering into {k} topics...")
        model = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = model.fit_predict(X)
        centers = model.cluster_centers_

        # Assign cluster to each record
        for i, rec in enumerate(records):
            rec["cluster"] = int(labels[i])

        # Gather examples for each cluster (sample broadly)
        cluster_items: dict[int, list[tuple[float, str]]] = defaultdict(list)
        for i, rec in enumerate(records):
            dist = np.linalg.norm(X[i] - centers[rec["cluster"]])
            cluster_items[rec["cluster"]].append((dist, rec["question"]))

        # Sample broadly from each cluster for labeling
        cluster_examples = {}
        for cluster_id, items in cluster_items.items():
            items.sort(key=lambda x: x[0])
            n_items = len(items)
            sampled = []
            if n_items >= 15:
                # 5 near, 5 mid, 5 far
                sampled.extend(items[:5])
                mid_start = n_items // 3
                sampled.extend(items[mid_start:mid_start + 5])
                sampled.extend(items[-5:])
            else:
                sampled = items
            cluster_examples[cluster_id] = [q[:80] for _, q in sampled]

        # Generate labels with one big GPT call for consistency
        print("Generating consistent topic labels...")
        topic_labels = self._generate_labels_batch(client, cluster_examples)

        # Build period x topic matrix
        periods = sorted(set(r["period"] for r in records))

        # Exclude current incomplete period
        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        current_period_num = (iso_week - 1) // self.period_weeks
        current_period = f"{iso_year}-P{current_period_num:02d}"
        periods = [p for p in periods if p < current_period]

        # Count per period per topic
        period_topic_counts = defaultdict(lambda: defaultdict(int))
        for rec in records:
            if rec["period"] in periods:
                period_topic_counts[rec["period"]][rec["cluster"]] += 1

        # Build data matrix for streamgraph
        # Sort topics by total count for better visualization
        topic_totals = defaultdict(int)
        for rec in records:
            topic_totals[rec["cluster"]] += 1
        sorted_topics = sorted(topic_totals.keys(), key=lambda t: -topic_totals[t])

        # Create CSV data
        csv_path = self.output_dir / "topic_stream_data.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            header = ["period"] + [topic_labels.get(t, "Diverse Queries") for t in sorted_topics]
            writer.writerow(header)
            for period in periods:
                row = [period] + [period_topic_counts[period][t] for t in sorted_topics]
                writer.writerow(row)

        # Generate streamgraph
        print("Generating streamgraph...")
        self._generate_streamgraph(
            periods, sorted_topics, period_topic_counts, topic_labels
        )

        # Build markdown output
        output_lines = ["# Topic Stream\n"]
        period_desc = f"{self.period_weeks}-week" if self.period_weeks > 1 else "weekly"
        output_lines.append(f"*{n:,} conversations across {len(periods)} {period_desc} periods, {k} topics*\n")
        output_lines.append("![Topic Stream](topic_stream.png)\n")

        output_lines.append("## Topic Legend\n")
        output_lines.append("| Color | Topic | Total |")
        output_lines.append("|-------|-------|------:|")

        colors = plt.cm.tab20(np.linspace(0, 1, len(sorted_topics)))
        for i, topic_id in enumerate(sorted_topics):
            label = topic_labels.get(topic_id, "Diverse Queries")
            total = topic_totals[topic_id]
            # Create color swatch using unicode block
            output_lines.append(f"| {i+1} | {label} | {total:,} |")

        output_lines.append(f"\n*Data exported to: topic_stream_data.csv*")

        self.write_output("\n".join(output_lines))

        return {
            "total_conversations": n,
            "periods": len(periods),
            "period_weeks": self.period_weeks,
            "topics": k,
        }

    def _extract_first_user_message(self, data: dict) -> dict | None:
        """Extract the first user message with timestamp."""
        mapping = data.get("mapping", {})
        messages = []

        for node in mapping.values():
            message = node.get("message")
            if message is None:
                continue

            author = message.get("author", {})
            if author.get("role") != "user":
                continue

            metadata = message.get("metadata", {})
            if metadata.get("is_visually_hidden_from_conversation"):
                continue

            content = message.get("content", {})
            if content.get("content_type") == "user_editable_context":
                continue

            parts = content.get("parts", [])
            text = "".join(p for p in parts if isinstance(p, str)).strip()

            if text and message.get("create_time", 0) > 0:
                messages.append({"time": message["create_time"], "text": text})

        if not messages:
            return None

        messages.sort(key=lambda x: x["time"])
        return messages[0]

    def _generate_labels_batch(self, client, cluster_examples: dict[int, list[str]]) -> dict[int, str]:
        """Generate all labels in one call for consistency."""
        lines = []
        for cluster_id in sorted(cluster_examples.keys()):
            examples = "; ".join(cluster_examples[cluster_id][:12])
            lines.append(f"{cluster_id}: {examples}")

        prompt = "\n".join(lines)

        # Save cluster examples for debugging
        debug_path = self.output_dir / "topic_stream_debug.txt"
        with open(debug_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("CLUSTER EXAMPLES SENT TO LLM\n")
            f.write("=" * 80 + "\n\n")
            for cluster_id in sorted(cluster_examples.keys()):
                f.write(f"Cluster {cluster_id}:\n")
                for i, ex in enumerate(cluster_examples[cluster_id][:12]):
                    f.write(f"  {i+1}. {ex}\n")
                f.write("\n")

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=600,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate short (2-3 word) labels for conversation topic clusters.

CRITICAL RULES:
- Labels must be CONCISE (2-3 words max) for chart readability
- Find the common theme across ALL examples (they're sampled from across each cluster)
- NEVER use generic labels like "Topic 1", "Topic 2", "Cluster A", "Miscellaneous", "General", "Other", "Various" - always find a specific theme
- ABSOLUTELY NO GEOGRAPHIC NAMES: No cities, countries, states, neighborhoods, landmarks
  - FORBIDDEN: "New York", "NYC", "Brooklyn", "Paris", "Japan", "Bay Area", etc.
  - Instead use: "Urban Exploration", "Local Events", "City Activities", "Travel Planning"
- ABSOLUTELY NO PERSON NAMES: No celebrities, authors, historical figures
  - FORBIDDEN: "Dan Ariely", "Elon Musk", "Shakespeare", etc.
  - Instead use: "Critical Analysis", "Tech Commentary", "Literary Analysis"
- ABSOLUTELY NO COMPANY/PRODUCT NAMES: No brand names, app names, service names
  - FORBIDDEN: "OpenAI API", "ChatGPT Help", "Netflix Shows", "Uber Tips"
  - Instead use: "AI Integration", "Chatbot Usage", "Streaming Media", "Rideshare Apps"
- Technology CATEGORIES are OK: "iOS Development", "Web Development", "Mobile Apps"
- Make labels describe the ACTIVITY or INTENT, not specific entities
- Make labels distinct from each other

Output format: one per line as 'N: Label'""",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            raw_response = resp.choices[0].message.content.strip()

            # Append raw LLM response to debug file
            with open(debug_path, "a") as f:
                f.write("=" * 80 + "\n")
                f.write("RAW LLM RESPONSE\n")
                f.write("=" * 80 + "\n\n")
                f.write(raw_response + "\n\n")

            labels = {}
            raw_labels = {}  # Store original labels before filtering

            # List of forbidden patterns (geographic, company names, etc.)
            # Note: Only use patterns that won't match legitimate words
            # Avoid short patterns like "la", "sf" that can match substrings
            forbidden_patterns = [
                "new york", "nyc", "brooklyn", "manhattan", "san francisco",
                "bay area", "los angeles", "chicago", "london", "paris",
                "tokyo", "berlin", "seattle", "boston", "austin", "denver",
                "openai", "chatgpt", "gpt-4", "anthropic", "google",
                "microsoft", "amazon", "facebook", "twitter",
                "netflix", "spotify", "uber", "airbnb", "tesla",
            ]

            for line in raw_response.split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    try:
                        cluster_id = int(parts[0].strip())
                        label = parts[1].strip()[:25]  # Truncate for chart
                        raw_labels[cluster_id] = label  # Store original

                        # Check for forbidden patterns and replace with generic
                        label_lower = label.lower()
                        needs_fix = any(pat in label_lower for pat in forbidden_patterns)

                        # Also check for generic labels the LLM might generate
                        generic_patterns = ["topic ", "cluster ", "miscellaneous", "general", "various", "other"]
                        if any(pat in label_lower for pat in generic_patterns):
                            needs_fix = True

                        if needs_fix:
                            # Request a new label for this specific cluster
                            label = self._regenerate_single_label(client, cluster_id, cluster_examples.get(cluster_id, []))

                        labels[cluster_id] = label
                    except ValueError:
                        continue

            # Log any labels that were replaced or missing
            with open(debug_path, "a") as f:
                f.write("=" * 80 + "\n")
                f.write("LABEL PROCESSING RESULTS\n")
                f.write("=" * 80 + "\n\n")
                for cluster_id in sorted(cluster_examples.keys()):
                    raw = raw_labels.get(cluster_id, "<MISSING FROM LLM RESPONSE>")
                    final = labels.get(cluster_id, f"Topic {cluster_id}")
                    if raw != final:
                        f.write(f"Cluster {cluster_id}: \"{raw}\" -> \"{final}\" (REPLACED)\n")
                    else:
                        f.write(f"Cluster {cluster_id}: \"{final}\"\n")

            # Fill in any missing labels
            for cluster_id in cluster_examples.keys():
                if cluster_id not in labels:
                    label = self._regenerate_single_label(client, cluster_id, cluster_examples.get(cluster_id, []))
                    labels[cluster_id] = label

            return labels
        except Exception as e:
            print(f"Warning: Could not generate labels: {e}")
            return {}

    def _regenerate_single_label(self, client, cluster_id: int, examples: list[str]) -> str:
        """Generate a label for a single cluster when the batch label was rejected."""
        if not examples:
            return "Diverse Queries"

        examples_text = "\n".join(f"- {ex[:100]}" for ex in examples[:8])

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=50,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate ONE short (2-3 word) label describing the common theme of these conversation starters.

Rules:
- Must be 2-3 words describing an ACTIVITY or INTENT
- NO generic labels (Topic, Cluster, Miscellaneous, General, Other, Various)
- NO named entities (people, places, companies, products)
- Find the underlying PURPOSE these queries share

Reply with ONLY the label, nothing else.""",
                    },
                    {"role": "user", "content": f"Conversation examples:\n{examples_text}"},
                ],
            )
            label = resp.choices[0].message.content.strip()[:25]

            # Final validation - reject if still generic
            if any(pat in label.lower() for pat in ["topic", "cluster", "misc", "general", "various", "other"]):
                return "Diverse Queries"

            return label
        except Exception:
            return "Diverse Queries"

    def _generate_streamgraph(
        self,
        periods: list[str],
        sorted_topics: list[int],
        period_topic_counts: dict,
        topic_labels: dict[int, str],
    ):
        """Generate streamgraph visualization with smooth curves."""
        from scipy.interpolate import make_interp_spline

        # Convert periods to dates (start of each period)
        dates = []
        for p in periods:
            # Parse period format: "2023-P01" -> date
            year, period_num = p.split("-P")
            # Convert period number back to week number (first week of period)
            first_week = int(period_num) * self.period_weeks + 1
            first_week = min(first_week, 52)  # Cap at week 52
            dates.append(datetime.strptime(f"{year}-W{first_week:02d}-1", "%G-W%V-%u"))
        x_numeric = mdates.date2num(dates)

        # Build data matrix
        data = np.array([
            [period_topic_counts[p][t] for p in periods]
            for t in sorted_topics
        ], dtype=float)

        # Smooth each topic's time series
        x_smooth = np.linspace(x_numeric.min(), x_numeric.max(), len(periods) * 3)
        data_smooth = np.zeros((len(sorted_topics), len(x_smooth)))

        for i in range(len(sorted_topics)):
            y = data[i]
            # Use lower degree spline (k=2) for smoother results with possible zeros
            k = min(2, len(y) - 1)
            if k > 0 and len(y) > 1:
                try:
                    spline = make_interp_spline(x_numeric, y, k=k)
                    y_smooth = spline(x_smooth)
                    # Clamp to non-negative (topics can't have negative counts)
                    y_smooth = np.maximum(y_smooth, 0)
                    # If original had zeros, try to preserve them (fade to zero)
                    data_smooth[i] = y_smooth
                except Exception:
                    data_smooth[i] = np.interp(x_smooth, x_numeric, y)
            else:
                data_smooth[i] = np.interp(x_smooth, x_numeric, y)

        # Convert smooth x back to dates
        dates_smooth = mdates.num2date(x_smooth)

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 8))

        # Use a nice colormap
        colors = plt.cm.tab20(np.linspace(0, 1, len(sorted_topics)))

        # Create streamgraph (stacked area with baseline='wiggle' for stream effect)
        ax.stackplot(
            dates_smooth,
            data_smooth,
            labels=[topic_labels.get(t, "Diverse Queries") for t in sorted_topics],
            colors=colors,
            baseline='wiggle',
            alpha=0.85
        )

        # Styling
        ax.set_title("Topic Trends Over Time", fontsize=16, fontweight="bold", pad=20)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        # Show monthly labels even though data is weekly
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # Remove spines
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.set_yticks([])

        # Legend outside
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            fontsize=9,
            frameon=False
        )

        plt.tight_layout()

        # Save
        plot_path = self.output_dir / "topic_stream.png"
        plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
