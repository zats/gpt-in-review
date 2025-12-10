"""Strategy for counting conversations, messages, etc."""

from typing import Any

from .base import Strategy


class BasicCountsStrategy(Strategy):
    """Count total conversations, messages by role, etc."""

    name = "basic_counts"
    description = "Count total conversations and messages"
    output_key = "static.overview"

    def run(self) -> dict[str, Any]:
        total_conversations = 0
        total_user_messages = 0
        total_assistant_messages = 0
        total_messages = 0

        for data in self.conversations:
            total_conversations += 1

            mapping = data.get("mapping", {})
            for node in mapping.values():
                message = node.get("message")
                if message is None:
                    continue

                author = message.get("author", {})
                role = author.get("role", "")

                # Skip hidden system messages
                metadata = message.get("metadata", {})
                if metadata.get("is_visually_hidden_from_conversation"):
                    continue

                total_messages += 1

                if role == "user":
                    total_user_messages += 1
                elif role == "assistant":
                    total_assistant_messages += 1

        avg_per_chat = total_messages / total_conversations if total_conversations > 0 else 0

        # Return data.json compatible structure
        return {
            "totalMessages": total_messages,
            "totalConversations": total_conversations,
            "userMessages": total_user_messages,
            "assistantMessages": total_assistant_messages,
            "avgPerChat": round(avg_per_chat, 1),
        }
