"""Strategy for clustering conversations into topics using embeddings."""

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI
from sklearn.cluster import KMeans

import google.genai as genai
from google.genai import types as genai_types

from .base import Strategy

# Tarot card image generation style prefix
TAROT_IMAGE_STYLE = """tarot card 9:16 ratio intricately detailed, mix in all the details into one fluid scene instead of placing elements all around make it look like a detailed Hieronymus Bosch painting, but less crowded

"""


class TopicClustersStrategy(Strategy):
    """Cluster conversations into topics using OpenAI embeddings."""

    name = "topic_clusters"
    description = "Find top 20 conversation topics using embedding clustering"

    def run(self) -> dict[str, Any]:
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Try loading from .env file
            env_path = self.conversations_dir.parent / "0_time_series" / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            os.environ["OPENAI_API_KEY"] = api_key
                            break

        if not api_key:
            error_msg = "OPENAI_API_KEY not found in environment or .env file"
            self.write_output(f"# Topic Clusters\n\nError: {error_msg}")
            return {"error": error_msg}

        files = self.get_conversation_files()
        records: list[dict[str, str]] = []
        skipped = 0

        # Extract first user message from each conversation
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                title = data.get("title") or "Untitled"
                first_user_msg = self._extract_first_user_message(data)

                if first_user_msg and len(first_user_msg.strip()) > 10:
                    records.append({
                        "file": file_path.name,
                        "title": title,
                        "question": first_user_msg,
                    })
                else:
                    skipped += 1

            except Exception as e:
                skipped += 1

        if not records:
            self.write_output("# Topic Clusters\n\nNo valid conversations found.")
            return {"error": "No valid conversations"}

        print(f"Processing {len(records)} conversations (skipped {skipped})...")

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
        k = min(50, max(10, n // 50))

        print(f"Clustering into {k} clusters...")
        model = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = model.fit_predict(X)
        centers = model.cluster_centers_

        # Group by cluster
        clusters: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)

        # Sort by size
        clusters_sorted = sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True)

        # Build top 20 clusters info
        top_n = 20
        cluster_summaries = []

        for rank, (label, idxs) in enumerate(clusters_sorted[:top_n], 1):
            size = len(idxs)
            pct = size / n * 100

            # Sample representatives from across the cluster (near, mid, far from center)
            members = np.array(idxs)
            dists = np.linalg.norm(X[members] - centers[label], axis=1)
            sorted_by_dist = members[np.argsort(dists)]

            # Take samples from different distances: 4 near, 4 mid, 4 far
            sample_indices = []
            n_members = len(sorted_by_dist)
            if n_members >= 12:
                sample_indices.extend(sorted_by_dist[:4])  # 4 nearest
                mid_start = n_members // 3
                sample_indices.extend(sorted_by_dist[mid_start:mid_start + 4])  # 4 middle
                sample_indices.extend(sorted_by_dist[-4:])  # 4 farthest
            else:
                sample_indices = sorted_by_dist[:min(12, n_members)]

            reps = [self._summarize_question(records[i]["question"]) for i in sample_indices]

            cluster_summaries.append({
                "rank": rank,
                "size": size,
                "pct": pct,
                "representatives": reps,
            })

        # Generate cluster labels using OpenAI
        print("Generating cluster labels...")
        cluster_labels = self._generate_cluster_labels(client, cluster_summaries)

        # Generate witty summary using OpenAI
        print("Generating witty summary...")
        cluster_list = self._format_clusters_for_prompt(cluster_summaries, cluster_labels)
        witty_summary = self._generate_witty_summary(client, cluster_list)

        # Generate tarot card image
        print("Generating tarot card image...")
        tarot_image_path = self._generate_tarot_image(witty_summary)

        # Build output
        output_lines = ["# Topic Clusters\n"]
        if tarot_image_path:
            output_lines.append(f"![Your Tarot Card](tarot_card.png)\n")
        output_lines.append(f"> {witty_summary}\n")
        output_lines.append(f"*Analyzed {n:,} conversations, clustered into {k} topics.*\n")

        output_lines.append("| % | Topic | Examples |")
        output_lines.append("|--:|-------|----------|")

        for cs in cluster_summaries:
            label = cluster_labels.get(cs["rank"], "Misc")
            examples = " • ".join(f'"{rep}"' for rep in cs["representatives"][:3])
            output_lines.append(f"| {cs['pct']:.1f}% | {label} | {examples} |")

        output_lines.append("")
        output_lines.append(f"*Clustering: KMeans with k={k}, embeddings: text-embedding-3-small*")

        self.write_output("\n".join(output_lines))

        return {
            "total_conversations": n,
            "clusters": k,
            "top_cluster_size": cluster_summaries[0]["size"] if cluster_summaries else 0,
        }

    def _extract_first_user_message(self, data: dict) -> str | None:
        """Extract the first user message from conversation JSON."""
        mapping = data.get("mapping", {})

        # Find messages and sort by create_time
        messages = []
        for node in mapping.values():
            message = node.get("message")
            if message is None:
                continue

            author = message.get("author", {})
            role = author.get("role", "")

            if role != "user":
                continue

            # Skip hidden messages
            metadata = message.get("metadata", {})
            if metadata.get("is_visually_hidden_from_conversation"):
                continue

            content = message.get("content", {})

            # Skip user_editable_context
            if content.get("content_type") == "user_editable_context":
                continue

            parts = content.get("parts", [])
            text = ""
            for part in parts:
                if isinstance(part, str):
                    text += part

            if text.strip():
                create_time = message.get("create_time") or 0
                messages.append((create_time, text.strip()))

        if not messages:
            return None

        # Return earliest message
        messages.sort(key=lambda x: x[0])
        return messages[0][1]

    def _summarize_question(self, q: str, limit: int = 120) -> str:
        """Truncate and clean up a question for display."""
        compact = " ".join(q.split())
        return compact if len(compact) <= limit else compact[: limit - 1] + "…"

    def _format_clusters_for_prompt(self, clusters: list[dict], labels: dict[int, str]) -> str:
        """Format cluster summaries for the OpenAI prompt."""
        lines = []
        for cs in clusters:
            label = labels.get(cs["rank"], "misc")
            lines.append(f"{cs['rank']}) {label} ({cs['size']})")
        return " ".join(lines)

    def _generate_cluster_labels(self, client, cluster_summaries: list[dict]) -> dict[int, str]:
        """Generate short human-readable labels for each cluster."""
        # Build prompt with all clusters - use all available examples
        cluster_descriptions = []
        for cs in cluster_summaries:
            # Use up to 10 examples to show the breadth of the cluster
            examples = "; ".join(cs["representatives"][:10])
            cluster_descriptions.append(f"{cs['rank']}: {examples}")

        prompt = "\n".join(cluster_descriptions)

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=500,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate a short (2-4 word) label for each conversation cluster.

IMPORTANT: The examples shown are sampled from across the entire cluster (some near center, some at edges).
Find the COMMON THEME that connects ALL examples, not just the first few.
Don't name the cluster after a specific person/tool if other examples don't mention them.

Output format: one label per line as 'N: Label'""",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            # Parse response
            labels = {}
            for line in resp.choices[0].message.content.strip().split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    try:
                        rank = int(parts[0].strip())
                        label = parts[1].strip()
                        labels[rank] = label
                    except ValueError:
                        continue
            return labels
        except Exception as e:
            print(f"Warning: Could not generate labels: {e}")
            return {}

    def _generate_witty_summary(self, client: OpenAI, cluster_list: str) -> str:
        """Generate a witty tarot-card reading summary."""
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

[Card illustration description, ~40 words. Include 3-5 concrete visual symbols drawn directly from their topics. Describe what the figure holds, wears, stands on/near.]

RULES:
- Pick a fitting Major Arcana card (The Magician, The Hermit, The Tower, etc.)
- Persona title should be creative and specific to their interests, not generic
- Illustration must have CONCRETE objects from their topics
- Reading should be playful but grounded in their actual themes
- Avoid generic mystical language like "journey", "path", "wisdom", "truth".""",
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

    def _generate_tarot_image(self, tarot_description: str) -> Path | None:
        """Generate a tarot card image using Nano Banana Pro (Gemini 3 Pro Image)."""
        # Check for API key
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Try loading from .env file
            env_path = self.conversations_dir.parent / "0_time_series" / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("GOOGLE_API_KEY=") or line.startswith("GEMINI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break

        if not api_key:
            print("Warning: GOOGLE_API_KEY not found, skipping image generation")
            return None

        try:
            # Build the full prompt
            full_prompt = TAROT_IMAGE_STYLE + tarot_description

            # Initialize client
            client = genai.Client(api_key=api_key)

            # Configure for image output with 9:16 aspect ratio for tarot card
            config = genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                temperature=1.0,
                image_config=genai_types.ImageConfig(aspect_ratio="9:16"),
            )

            # Generate image (non-streaming for simpler handling)
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=full_prompt,
                config=config,
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    output_path = self.output_dir / "tarot_card.png"
                    with open(output_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    print(f"Tarot card image saved: {output_path}")
                    return output_path

            print("Warning: No image data received from API")
            return None

        except Exception as e:
            print(f"Warning: Could not generate tarot image: {e}")
            return None
