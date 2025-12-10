"""Strategy for analyzing emoji usage by user and assistant."""

import json
import math
import unicodedata
from collections import Counter
from typing import Any

import emoji

from .base import Strategy


def normalize_emoji(e: str) -> str:
    """Normalize emoji by ensuring emoji presentation (VS16).

    Removes any existing variation selectors first, then adds VS16 (U+FE0F)
    to ensure consistent emoji-style rendering.
    """
    # Remove existing variation selectors
    base = e.replace('\ufe0e', '').replace('\ufe0f', '')
    # Add emoji variation selector (VS16) for better visual presentation
    return base + '\ufe0f'


class EmojiStatsStrategy(Strategy):
    """Analyze emoji usage patterns by user and assistant."""

    name = "emoji_stats"
    description = "Top emojis used by user and assistant"

    # Configuration
    top_n: int = 40  # Number of top emojis to show

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        user_emojis: Counter = Counter()
        assistant_emojis: Counter = Counter()
        user_message_count = 0
        assistant_message_count = 0

        print("Analyzing emoji usage...")
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                messages = self._extract_messages(data)

                for msg in messages:
                    role = msg["role"]
                    text = msg["text"]

                    # Extract all emojis from text
                    found_emojis = emoji.emoji_list(text)

                    if role == "user":
                        user_message_count += 1
                        for e in found_emojis:
                            user_emojis[normalize_emoji(e["emoji"])] += 1
                    elif role == "assistant":
                        assistant_message_count += 1
                        for e in found_emojis:
                            assistant_emojis[normalize_emoji(e["emoji"])] += 1

            except Exception:
                pass

        # Get top N emojis
        top_user = user_emojis.most_common(self.top_n)
        top_assistant = assistant_emojis.most_common(self.top_n)

        # Calculate totals
        total_user_emojis = sum(user_emojis.values())
        total_assistant_emojis = sum(assistant_emojis.values())
        unique_user_emojis = len(user_emojis)
        unique_assistant_emojis = len(assistant_emojis)

        # Compare user vs assistant emoji usage
        comparison = self._compare_emoji_usage(total_user_emojis, total_assistant_emojis)

        # Build output
        output_lines = ["# Emoji Stats\n"]
        output_lines.append(f"*Analyzed {len(files):,} conversations*\n")

        # Add comparison insight at the top
        output_lines.append(f"> {comparison}\n")

        # User section
        output_lines.append("## User Emojis\n")
        output_lines.append(f"- **Total emojis used:** {total_user_emojis:,}")
        output_lines.append(f"- **Unique emojis:** {unique_user_emojis:,}")
        output_lines.append(f"- **Messages analyzed:** {user_message_count:,}\n")

        if top_user:
            output_lines.append(f"### Top {self.top_n} User Emojis\n")
            output_lines.append("| Rank | Emoji | Count |")
            output_lines.append("|-----:|:-----:|------:|")
            for i, (emj, count) in enumerate(top_user, 1):
                output_lines.append(f"| {i} | {emj} | {count:,} |")
        else:
            output_lines.append("*No emojis found in user messages.*")

        output_lines.append("")

        # Assistant section
        output_lines.append("## Assistant Emojis\n")
        output_lines.append(f"- **Total emojis used:** {total_assistant_emojis:,}")
        output_lines.append(f"- **Unique emojis:** {unique_assistant_emojis:,}")
        output_lines.append(f"- **Messages analyzed:** {assistant_message_count:,}\n")

        if top_assistant:
            output_lines.append(f"### Top {self.top_n} Assistant Emojis\n")
            output_lines.append("| Rank | Emoji | Count |")
            output_lines.append("|-----:|:-----:|------:|")
            for i, (emj, count) in enumerate(top_assistant, 1):
                output_lines.append(f"| {i} | {emj} | {count:,} |")
        else:
            output_lines.append("*No emojis found in assistant messages.*")

        self.write_output("\n".join(output_lines))

        # Return raw data for potential further use
        return {
            "user": {
                "total": total_user_emojis,
                "unique": unique_user_emojis,
                "messages": user_message_count,
                "top": top_user,
                "all": dict(user_emojis),
            },
            "assistant": {
                "total": total_assistant_emojis,
                "unique": unique_assistant_emojis,
                "messages": assistant_message_count,
                "top": top_assistant,
                "all": dict(assistant_emojis),
            },
        }

    def _extract_messages(self, data: dict) -> list[dict]:
        """Extract all messages with role and text."""
        mapping = data.get("mapping", {})
        messages = []

        for node in mapping.values():
            message = node.get("message")
            if message is None:
                continue

            author = message.get("author", {})
            role = author.get("role")

            if role not in ("user", "assistant"):
                continue

            # Skip hidden messages
            metadata = message.get("metadata", {})
            if metadata.get("is_visually_hidden_from_conversation"):
                continue

            content = message.get("content", {})
            if content.get("content_type") == "user_editable_context":
                continue

            parts = content.get("parts", [])
            text = "".join(p for p in parts if isinstance(p, str))

            if text:
                messages.append({"role": role, "text": text})

        return messages

    def _compare_emoji_usage(self, user_count: int, assistant_count: int) -> str:
        """Compare emoji usage between user and assistant.

        Returns a human-readable insight about the comparison.

        Logic:
        - If different orders of magnitude: clearly one is more
        - If same order of magnitude: check if delta is within half of the order
        """
        # Handle edge cases
        if user_count == 0 and assistant_count == 0:
            return "Neither you nor the assistant used any emojis. All business, no play!"
        if user_count == 0:
            return "You didn't use any emojis, but the assistant sprinkled in a few. Maybe loosen up a bit? 😉"
        if assistant_count == 0:
            return "You used emojis but the assistant stayed strictly professional. Not a single emoji in return!"

        # Determine order of magnitude for each
        user_magnitude = math.floor(math.log10(user_count))
        assistant_magnitude = math.floor(math.log10(assistant_count))

        # If different orders of magnitude, clearly different
        if abs(user_magnitude - assistant_magnitude) >= 1:
            if user_count > assistant_count:
                return f"You really embraced the emoji life with {user_count:,} emojis, while the assistant barely used any ({assistant_count:,}). The enthusiasm wasn't quite matched!"
            else:
                return f"The assistant went all-in with {assistant_count:,} emojis while you kept it minimal at {user_count:,}. Someone was doing the expressive heavy lifting!"

        # Same order of magnitude - check if within threshold
        max_count = max(user_count, assistant_count)
        order_of_magnitude = 10 ** math.floor(math.log10(max_count))
        threshold = order_of_magnitude / 2
        delta = abs(user_count - assistant_count)

        if delta <= threshold:
            return f"You and the assistant were on the same wavelength! Both used emojis at a similar rate ({user_count:,} vs {assistant_count:,}). Great emoji synergy! ✨"
        elif user_count > assistant_count:
            return f"You brought the emoji energy with {user_count:,}, but the assistant was a bit more reserved at {assistant_count:,}. Your expressiveness wasn't fully reciprocated!"
        else:
            return f"The assistant was more emoji-forward ({assistant_count:,}) compared to your {user_count:,}. They were really trying to brighten up the conversation!"
