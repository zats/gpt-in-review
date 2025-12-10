"""Strategy for analyzing emoji usage by user and assistant."""

from collections import Counter
from typing import Any

import emoji

from .base import Strategy


def normalize_emoji(e: str) -> str:
    """Normalize emoji by ensuring emoji presentation (VS16)."""
    base = e.replace('\ufe0e', '').replace('\ufe0f', '')
    return base + '\ufe0f'


class EmojiStatsStrategy(Strategy):
    """Analyze emoji usage patterns by user and assistant."""

    name = "emoji_stats"
    description = "Top emojis used by user and assistant"
    output_key = "emojis"

    TOP_N = 40

    def run(self) -> dict[str, Any]:
        user_emojis: Counter = Counter()
        assistant_emojis: Counter = Counter()

        for data in self.conversations:
            mapping = data.get("mapping", {})

            for node in mapping.values():
                message = node.get("message")
                if message is None:
                    continue

                author = message.get("author", {})
                role = author.get("role")
                if role not in ("user", "assistant"):
                    continue

                metadata = message.get("metadata", {})
                if metadata.get("is_visually_hidden_from_conversation"):
                    continue

                content = message.get("content", {})
                if content.get("content_type") == "user_editable_context":
                    continue

                parts = content.get("parts", [])
                text = "".join(p for p in parts if isinstance(p, str))

                if not text:
                    continue

                # Extract all emojis from text
                found_emojis = emoji.emoji_list(text)

                if role == "user":
                    for e in found_emojis:
                        user_emojis[normalize_emoji(e["emoji"])] += 1
                elif role == "assistant":
                    for e in found_emojis:
                        assistant_emojis[normalize_emoji(e["emoji"])] += 1

        # Get top N emojis
        top_user = user_emojis.most_common(self.TOP_N)
        top_assistant = assistant_emojis.most_common(self.TOP_N)

        # Calculate totals
        total_user = sum(user_emojis.values())
        total_assistant = sum(assistant_emojis.values())

        # Format for data.json (list of [emoji, count] pairs)
        return {
            "user": {
                "total": total_user,
                "emojis": [[e, c] for e, c in top_user],
            },
            "assistant": {
                "total": total_assistant,
                "emojis": [[e, c] for e, c in top_assistant],
            },
        }
