"""Strategy for showing topic evolution over time - Topic Time Machine."""

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI
from sklearn.cluster import KMeans

from .base import Strategy


class TopicTimelineStrategy(Strategy):
    """Show how conversation topics evolved week by week."""

    name = "topic_timeline"
    description = "Topic Time Machine - see how your interests evolved over time"

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
            self.write_output(f"# Topic Timeline\n\nError: {error_msg}")
            return {"error": error_msg}

        files = self.get_conversation_files()
        records: list[dict] = []

        # Extract first user message and timestamp from each conversation
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                first_msg = self._extract_first_user_message(data)
                if not first_msg or len(first_msg["text"].strip()) < 10:
                    continue

                records.append({
                    "file": file_path.name,
                    "question": first_msg["text"],
                    "timestamp": first_msg["time"],
                    "week": self._get_week_key(first_msg["time"]),
                })

            except Exception as e:
                pass

        if not records:
            self.write_output("# Topic Timeline\n\nNo valid conversations found.")
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

        # Use ~25 clusters for topic diversity
        k = min(25, max(8, n // 100))

        print(f"Clustering into {k} topics...")
        model = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = model.fit_predict(X)
        centers = model.cluster_centers_

        # Assign cluster labels to records
        for i, rec in enumerate(records):
            rec["cluster"] = int(labels[i])

        # Find representative questions for each cluster (for labeling)
        cluster_reps: dict[int, list[str]] = defaultdict(list)
        for i, rec in enumerate(records):
            dist = np.linalg.norm(X[i] - centers[rec["cluster"]])
            cluster_reps[rec["cluster"]].append((dist, rec["question"]))

        # Sample from across each cluster: near, mid, far from center
        cluster_examples = {}
        for cluster_id, items in cluster_reps.items():
            items.sort(key=lambda x: x[0])
            n_items = len(items)
            sampled = []
            if n_items >= 12:
                # 4 near, 4 mid, 4 far
                sampled.extend(items[:4])
                mid_start = n_items // 3
                sampled.extend(items[mid_start:mid_start + 4])
                sampled.extend(items[-4:])
            else:
                sampled = items[:min(12, n_items)]
            cluster_examples[cluster_id] = [q[:100] for _, q in sampled]

        # Generate labels for clusters
        print("Generating topic labels...")
        topic_labels = self._generate_topic_labels(client, cluster_examples)

        # Group by week
        weeks = defaultdict(list)
        for rec in records:
            weeks[rec["week"]].append(rec)

        # Sort weeks chronologically
        sorted_weeks = sorted(weeks.keys())

        # Build timeline data
        timeline_data = []
        for week in sorted_weeks:
            week_records = weeks[week]
            topic_counts = defaultdict(int)
            for rec in week_records:
                topic_counts[rec["cluster"]] += 1

            # Sort by count, get top topics for this week
            top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])
            timeline_data.append({
                "week": week,
                "total": len(week_records),
                "topics": [(topic_labels.get(tid, f"Topic {tid}"), count) for tid, count in top_topics[:5]],
            })

        # Build output
        output_lines = ["# Topic Time Machine\n"]
        output_lines.append(f"*Tracking {n:,} conversations across {len(sorted_weeks)} weeks*\n")
        output_lines.append("---\n")

        for entry in timeline_data:
            week_date = datetime.strptime(entry["week"] + "-1", "%Y-%W-%w")
            week_label = week_date.strftime("%b %d, %Y")

            output_lines.append(f"### Week of {week_label}")
            output_lines.append(f"*{entry['total']} conversations*\n")

            topic_strs = []
            for topic_name, count in entry["topics"]:
                if count > 1:
                    topic_strs.append(f"**{topic_name}** ({count})")
                else:
                    topic_strs.append(f"{topic_name}")

            output_lines.append(" · ".join(topic_strs))
            output_lines.append("")

        # Add topic legend at the end
        output_lines.append("---\n")
        output_lines.append("## All Topics\n")
        output_lines.append("| Topic | Example Questions |")
        output_lines.append("|-------|-------------------|")
        for cluster_id in sorted(topic_labels.keys()):
            label = topic_labels[cluster_id]
            examples = " / ".join(cluster_examples.get(cluster_id, [])[:2])
            if len(examples) > 80:
                examples = examples[:80] + "…"
            output_lines.append(f"| {label} | {examples} |")

        self.write_output("\n".join(output_lines))

        return {
            "total_conversations": n,
            "weeks": len(sorted_weeks),
            "topics": k,
        }

    def _extract_first_user_message(self, data: dict) -> dict | None:
        """Extract the first user message with timestamp from conversation."""
        mapping = data.get("mapping", {})
        messages = []

        for node in mapping.values():
            message = node.get("message")
            if message is None:
                continue

            author = message.get("author", {})
            role = author.get("role", "")
            if role != "user":
                continue

            metadata = message.get("metadata", {})
            if metadata.get("is_visually_hidden_from_conversation"):
                continue

            content = message.get("content", {})
            if content.get("content_type") == "user_editable_context":
                continue

            parts = content.get("parts", [])
            text = ""
            for part in parts:
                if isinstance(part, str):
                    text += part

            if text.strip():
                create_time = message.get("create_time") or 0
                if create_time > 0:
                    messages.append({"time": create_time, "text": text.strip()})

        if not messages:
            return None

        messages.sort(key=lambda x: x["time"])
        return messages[0]

    def _get_week_key(self, timestamp: float) -> str:
        """Convert timestamp to week key (YYYY-WW format)."""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%W")

    def _generate_topic_labels(self, client, cluster_examples: dict[int, list[str]]) -> dict[int, str]:
        """Generate short labels for each cluster."""
        # Build prompt - use all available examples
        lines = []
        for cluster_id in sorted(cluster_examples.keys()):
            examples = "; ".join(cluster_examples[cluster_id][:10])
            lines.append(f"{cluster_id}: {examples}")

        prompt = "\n".join(lines)

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=800,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate a short (2-4 word) label for each conversation cluster.

IMPORTANT: The examples shown are sampled from across the entire cluster (some near center, some at edges).
Find the COMMON THEME that connects ALL examples, not just the first few.
Don't name the cluster after a specific person/tool if other examples don't mention them.

Output format: one label per line as 'N: Label'""",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            labels = {}
            for line in resp.choices[0].message.content.strip().split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    try:
                        cluster_id = int(parts[0].strip())
                        label = parts[1].strip()
                        labels[cluster_id] = label
                    except ValueError:
                        continue
            return labels
        except Exception as e:
            print(f"Warning: Could not generate labels: {e}")
            return {}
