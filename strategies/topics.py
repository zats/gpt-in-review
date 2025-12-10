"""Strategy for topic analysis: clustering, labels, streamgraph, and tarot card."""

import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI
from sklearn.cluster import KMeans

import google.genai as genai
from google.genai import types as genai_types

from .base import Strategy

# Tarot card image generation style prefix
TAROT_IMAGE_STYLE = """tarot card 9:16 ratio intricately detailed, mix in all the details into one fluid scene instead of placing elements all around make it look like a 70s stock photo from the office promo materials photoshoot. Just create the photo, no text borders

"""


class TopicsStrategy(Strategy):
    """Unified topic analysis: embeddings once, outputs topics + streamgraph + tarot."""

    name = "topics"
    description = "Topic clustering, streamgraph, and tarot card generation"
    output_key = "topics"  # Actually outputs multiple keys, handled in main.py

    # Streamgraph settings
    STREAMGRAPH_TOPICS = 10
    PERIOD_WEEKS = 2

    def run(self) -> dict[str, Any]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return self._empty_result("OPENAI_API_KEY not found")

        # Extract first user message from each conversation (with timestamp)
        records = self._extract_records()
        if not records:
            return self._empty_result("No valid conversations")

        # Get embeddings ONCE for all records
        client = OpenAI()
        embeddings = self._get_embeddings(client, records)
        X = np.array(embeddings)
        n = len(records)

        # === TOPIC CLUSTERS (k=50) for top topics + tarot ===
        k_topics = min(50, max(10, n // 50))
        topics_model = KMeans(n_clusters=k_topics, random_state=42, n_init="auto")
        topics_labels = topics_model.fit_predict(X)
        topics_centers = topics_model.cluster_centers_

        # Build cluster summaries for top 20
        cluster_summaries = self._build_cluster_summaries(
            records, X, topics_labels, topics_centers, top_n=20
        )

        # Generate labels for topic clusters
        topic_cluster_labels = self._generate_cluster_labels(client, cluster_summaries)

        # Build topics list (top 10 for website)
        topics_list = []
        for cs in cluster_summaries[:10]:
            label = topic_cluster_labels.get(cs["rank"], "Misc")
            topics_list.append({
                "rank": cs["rank"],
                "name": label,
                "pct": round(cs["pct"], 1),
            })

        # Generate tarot card
        cluster_list = self._format_clusters_for_prompt(cluster_summaries, topic_cluster_labels)
        witty_summary = self._generate_witty_summary(client, cluster_list)
        self._generate_tarot_image(witty_summary)
        tarot_info = self._parse_tarot_info(witty_summary)

        # === STREAMGRAPH (k=10) for time-based trends ===
        k_stream = min(self.STREAMGRAPH_TOPICS, n // 50)
        k_stream = max(3, k_stream)
        stream_model = KMeans(n_clusters=k_stream, random_state=42, n_init="auto")
        stream_labels = stream_model.fit_predict(X)
        stream_centers = stream_model.cluster_centers_

        # Assign stream cluster to each record
        for i, rec in enumerate(records):
            rec["stream_cluster"] = int(stream_labels[i])

        # Gather examples for streamgraph labels
        stream_examples = self._gather_cluster_examples(records, X, stream_centers, "stream_cluster")

        # Generate streamgraph labels
        stream_topic_labels = self._generate_stream_labels(client, stream_examples)

        # Build streamgraph data
        streamgraph = self._build_streamgraph(records, stream_topic_labels)

        return {
            "topics": topics_list,
            "tarot": {
                "image": "tarot_card.png",
                "title": tarot_info.get("card", "The Magician"),
                "subtitle": tarot_info.get("persona", "Code Alchemist"),
            },
            "streamgraph": streamgraph,
        }

    def _empty_result(self, error: str) -> dict[str, Any]:
        """Return empty structure on error."""
        return {
            "error": error,
            "topics": [],
            "tarot": {},
            "streamgraph": {"periods": [], "keys": [], "values": []},
        }

    def _extract_records(self) -> list[dict]:
        """Extract first user message with timestamp from each conversation."""
        records = []

        for data in self.conversations:
            title = data.get("title") or "Untitled"
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

                if text and len(text) > 10:
                    create_time = message.get("create_time") or 0
                    if create_time > 0:
                        messages.append({"time": create_time, "text": text})

            if messages:
                messages.sort(key=lambda x: x["time"])
                first = messages[0]

                # Calculate period for streamgraph
                dt = datetime.fromtimestamp(first["time"])
                iso_year, iso_week, _ = dt.isocalendar()
                period_num = (iso_week - 1) // self.PERIOD_WEEKS
                period_key = f"{iso_year}-P{period_num:02d}"

                records.append({
                    "title": title,
                    "question": first["text"],
                    "timestamp": first["time"],
                    "period": period_key,
                })

        return records

    def _get_embeddings(self, client: OpenAI, records: list[dict]) -> list[list[float]]:
        """Get embeddings for all records in batches."""
        batch_size = 100
        embeddings = []

        for start in range(0, len(records), batch_size):
            end = min(start + batch_size, len(records))
            batch = [r["question"][:1200] for r in records[start:end]]
            resp = client.embeddings.create(model="text-embedding-3-small", input=batch)
            ordered = sorted(resp.data, key=lambda d: d.index)
            embeddings.extend([item.embedding for item in ordered])

        return embeddings

    def _build_cluster_summaries(
        self, records: list[dict], X: np.ndarray, labels: np.ndarray,
        centers: np.ndarray, top_n: int
    ) -> list[dict]:
        """Build cluster summaries with representatives."""
        n = len(records)

        # Group by cluster
        clusters: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)

        # Sort by size
        clusters_sorted = sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True)

        summaries = []
        for rank, (label, idxs) in enumerate(clusters_sorted[:top_n], 1):
            size = len(idxs)
            pct = size / n * 100

            # Sample representatives (near center, middle, far)
            members = np.array(idxs)
            dists = np.linalg.norm(X[members] - centers[label], axis=1)
            sorted_by_dist = members[np.argsort(dists)]

            sample_indices = []
            n_members = len(sorted_by_dist)
            if n_members >= 12:
                sample_indices.extend(sorted_by_dist[:4])
                mid_start = n_members // 3
                sample_indices.extend(sorted_by_dist[mid_start:mid_start + 4])
                sample_indices.extend(sorted_by_dist[-4:])
            else:
                sample_indices = sorted_by_dist[:min(12, n_members)]

            reps = [self._summarize_question(records[i]["question"]) for i in sample_indices]

            summaries.append({
                "rank": rank,
                "size": size,
                "pct": pct,
                "representatives": reps,
            })

        return summaries

    def _summarize_question(self, q: str, limit: int = 120) -> str:
        """Truncate and clean up a question for display."""
        compact = " ".join(q.split())
        return compact if len(compact) <= limit else compact[:limit - 1] + "…"

    def _generate_cluster_labels(self, client: OpenAI, summaries: list[dict]) -> dict[int, str]:
        """Generate labels for topic clusters."""
        descriptions = []
        for cs in summaries:
            examples = "; ".join(cs["representatives"][:10])
            descriptions.append(f"{cs['rank']}: {examples}")

        prompt = "\n".join(descriptions)

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=500,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate a short (2-4 word) label for each conversation cluster.
Find the COMMON THEME that connects ALL examples.
Add a touch of wit or light sarcasm while staying accurate to the content.
Examples: Debugging Desperation, Recipe Rescue Ops, Existential Code Crisis
Output format: one label per line as 'N: Label'
IMPORTANT: Plain text only. No markdown, no asterisks, no quotes, no formatting.""",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            labels = {}
            for line in resp.choices[0].message.content.strip().split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    try:
                        rank = int(parts[0].strip())
                        label = parts[1].strip().strip('*"\'')  # Remove markdown/quotes
                        labels[rank] = label
                    except ValueError:
                        continue
            return labels
        except Exception:
            return {}

    def _format_clusters_for_prompt(self, summaries: list[dict], labels: dict[int, str]) -> str:
        """Format cluster summaries for tarot prompt."""
        lines = []
        for cs in summaries:
            label = labels.get(cs["rank"], "misc")
            lines.append(f"{cs['rank']}) {label} ({cs['size']})")
        return " ".join(lines)

    def _generate_witty_summary(self, client: OpenAI, cluster_list: str) -> str:
        """Generate tarot card reading summary."""
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=250,
                messages=[
                    {
                        "role": "system",
                        "content": """Create a tarot card reading based on these conversation clusters.

Output format (use markdown):
**[MAJOR ARCANA CARD]** — *[Creative 2-3 word persona title]*

[Card illustration description, ~40 words. Include 3-5 concrete visual symbols drawn directly from their topics.]

RULES:
- Pick a fitting Major Arcana card (The Magician, The Hermit, The Tower, etc.)
- Persona title should be creative and specific to their interests
- Illustration must have CONCRETE objects from their topics
- Avoid generic mystical language""",
                    },
                    {
                        "role": "user",
                        "content": f"Top 20 conversation clusters: {cluster_list}",
                    },
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"(Could not generate summary: {e})"

    def _parse_tarot_info(self, summary: str) -> dict:
        """Parse tarot card name and persona from summary."""
        import re

        card_match = re.search(r"\*\*([^*]+)\*\*", summary)
        card = card_match.group(1) if card_match else "The Magician"

        persona_match = re.search(r"—\s*\*([^*]+)\*", summary)
        persona = persona_match.group(1) if persona_match else "Code Alchemist"

        return {"card": card.strip(), "persona": persona.strip()}

    def _generate_tarot_image(self, tarot_description: str):
        """Generate tarot card image using Gemini."""
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        try:
            full_prompt = TAROT_IMAGE_STYLE + tarot_description
            client = genai.Client(api_key=api_key)

            config = genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                temperature=1.0,
                image_config=genai_types.ImageConfig(aspect_ratio="9:16"),
            )

            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=full_prompt,
                config=config,
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    website_dir = Path(__file__).parent.parent / "website"
                    website_dir.mkdir(exist_ok=True)
                    output_path = website_dir / "tarot_card.png"
                    with open(output_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    return output_path

            return None
        except Exception:
            return None

    def _gather_cluster_examples(
        self, records: list[dict], X: np.ndarray, centers: np.ndarray, cluster_key: str
    ) -> dict[int, list[str]]:
        """Gather example questions for each cluster."""
        cluster_items: dict[int, list[tuple[float, str]]] = defaultdict(list)
        for i, rec in enumerate(records):
            cluster_id = rec[cluster_key]
            dist = np.linalg.norm(X[i] - centers[cluster_id])
            cluster_items[cluster_id].append((dist, rec["question"]))

        examples = {}
        for cluster_id, items in cluster_items.items():
            items.sort(key=lambda x: x[0])
            n_items = len(items)
            sampled = []
            if n_items >= 15:
                sampled.extend(items[:5])
                mid_start = n_items // 3
                sampled.extend(items[mid_start:mid_start + 5])
                sampled.extend(items[-5:])
            else:
                sampled = items
            examples[cluster_id] = [q[:80] for _, q in sampled]

        return examples

    def _generate_stream_labels(self, client: OpenAI, examples: dict[int, list[str]]) -> dict[int, str]:
        """Generate labels for streamgraph clusters."""
        lines = []
        for cluster_id in sorted(examples.keys()):
            exs = "; ".join(examples[cluster_id][:12])
            lines.append(f"{cluster_id}: {exs}")

        prompt = "\n".join(lines)

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=600,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate short (2-3 word) labels for conversation topic clusters.

Rules:
- Labels must be CONCISE (2-3 words max)
- Find the common theme across ALL examples
- Add a touch of wit or light sarcasm while staying accurate
- NO generic labels (Topic, Cluster, Miscellaneous, General, Other, Various)
- NO named entities (people, places, companies, products)
- Describe the ACTIVITY or INTENT
- Examples: Debugging Desperation, Recipe Rescue, Code Therapy

Output format: one per line as 'N: Label'
IMPORTANT: Plain text only. No markdown, no asterisks, no quotes, no formatting.""",
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
                        label = parts[1].strip().strip('*"\'')[:25]  # Remove markdown/quotes
                        labels[cluster_id] = label
                    except ValueError:
                        continue

            for cluster_id in examples.keys():
                if cluster_id not in labels:
                    labels[cluster_id] = "Diverse Queries"

            return labels
        except Exception:
            return {cid: "Diverse Queries" for cid in examples.keys()}

    def _build_streamgraph(self, records: list[dict], labels: dict[int, str]) -> dict[str, Any]:
        """Build streamgraph data structure."""
        # Get periods, excluding current incomplete one
        periods = sorted(set(r["period"] for r in records))

        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        current_period_num = (iso_week - 1) // self.PERIOD_WEEKS
        current_period = f"{iso_year}-P{current_period_num:02d}"
        periods = [p for p in periods if p < current_period]

        # Count per period per topic
        period_topic_counts = defaultdict(lambda: defaultdict(int))
        for rec in records:
            if rec["period"] in periods:
                period_topic_counts[rec["period"]][rec["stream_cluster"]] += 1

        # Sort topics by total count
        topic_totals = defaultdict(int)
        for rec in records:
            topic_totals[rec["stream_cluster"]] += 1
        sorted_topics = sorted(topic_totals.keys(), key=lambda t: -topic_totals[t])

        # Build output
        keys = [labels.get(t, "Diverse Queries") for t in sorted_topics]

        values = []
        for period in periods:
            row = {"period": period}
            for t in sorted_topics:
                label = labels.get(t, "Diverse Queries")
                row[label] = period_topic_counts[period][t]
            values.append(row)

        return {
            "periods": periods,
            "keys": keys,
            "values": values,
        }
