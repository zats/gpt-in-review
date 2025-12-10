"""Strategy for finding shortest and longest assistant responses."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import Strategy


class ResponseLengthsStrategy(Strategy):
    """Find the shortest and longest assistant responses."""

    name = "response_lengths"
    description = "Find shortest and longest assistant text responses"

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        all_responses = []

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                title = data.get("title") or "Untitled"
                create_time = data.get("create_time")

                mapping = data.get("mapping", {})

                for node in mapping.values():
                    message = node.get("message")
                    if message is None:
                        continue

                    author = message.get("author", {})
                    role = author.get("role", "")

                    if role != "assistant":
                        continue

                    # Skip hidden messages
                    metadata = message.get("metadata", {})
                    if metadata.get("is_visually_hidden_from_conversation"):
                        continue

                    content = message.get("content", {})

                    # Only count text content type
                    if content.get("content_type") != "text":
                        continue

                    parts = content.get("parts", [])
                    text = ""
                    for part in parts:
                        if isinstance(part, str):
                            text += part

                    # Skip empty responses
                    if not text.strip():
                        continue

                    all_responses.append({
                        "title": title,
                        "filename": file_path.name,
                        "create_time": create_time,
                        "text": text,
                        "length": len(text),
                    })

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        if not all_responses:
            self.write_output("# Response Lengths\n\nNo responses found.")
            return {"error": "No responses found"}

        # Sort by length
        by_length = sorted(all_responses, key=lambda x: x["length"])

        # Get shortest (non-empty) and longest
        shortest = by_length[:20]
        longest = by_length[-20:][::-1]

        def format_timestamp(ts: float | None) -> str:
            if ts is None:
                return "unknown"
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

        def escape_markdown(text: str) -> str:
            return text.replace("|", "\\|").replace("\n", " ↵ ")

        # Build output
        output_lines = ["# Response Lengths\n"]

        # Shortest responses
        output_lines.append("## Shortest Assistant Responses\n")
        for i, r in enumerate(shortest, 1):
            escaped_text = escape_markdown(r["text"])
            output_lines.append(f"### {i}. {r['title'][:50]} ({r['length']} chars)\n")
            output_lines.append(f"**Date:** {format_timestamp(r['create_time'])}\n")
            output_lines.append(f"**Full response:**\n```\n{r['text']}\n```\n")

        # Longest responses
        output_lines.append("\n## Longest Assistant Responses\n")
        for i, r in enumerate(longest, 1):
            preview = r["text"][:300]
            if len(r["text"]) > 300:
                preview += "..."
            output_lines.append(f"### {i}. {r['title'][:50]} ({r['length']:,} chars)\n")
            output_lines.append(f"**Date:** {format_timestamp(r['create_time'])}\n")
            output_lines.append(f"**Preview (first 300 chars):**\n```\n{preview}\n```\n")

        # Stats
        lengths = [r["length"] for r in all_responses]
        avg_length = sum(lengths) / len(lengths)

        output_lines.append("\n## Statistics\n")
        output_lines.append(f"- **Total responses analyzed:** {len(all_responses):,}")
        output_lines.append(f"- **Shortest:** {min(lengths):,} chars")
        output_lines.append(f"- **Longest:** {max(lengths):,} chars")
        output_lines.append(f"- **Average:** {avg_length:,.0f} chars")

        self.write_output("\n".join(output_lines))

        return {
            "total_responses": len(all_responses),
            "shortest_length": min(lengths),
            "longest_length": max(lengths),
            "avg_length": avg_length,
        }
