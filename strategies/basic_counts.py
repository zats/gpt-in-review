"""Strategy for counting conversations, messages, etc."""

import json
from pathlib import Path
from typing import Any

from .base import Strategy


class BasicCountsStrategy(Strategy):
    """Count total conversations, messages by role, etc."""

    name = "basic_counts"
    description = "Count total conversations and messages"

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        total_conversations = 0
        total_user_messages = 0
        total_assistant_messages = 0
        total_system_messages = 0
        total_messages = 0

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

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
                    elif role == "system":
                        total_system_messages += 1

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        results = {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_user_messages": total_user_messages,
            "total_assistant_messages": total_assistant_messages,
            "total_system_messages": total_system_messages,
            "avg_messages_per_conversation": (
                total_messages / total_conversations if total_conversations > 0 else 0
            ),
        }

        # Write output
        output = f"""# Basic Counts

## Summary

| Metric | Count |
|--------|-------|
| Total Conversations | {results['total_conversations']:,} |
| Total Messages | {results['total_messages']:,} |
| User Messages | {results['total_user_messages']:,} |
| Assistant Messages | {results['total_assistant_messages']:,} |
| System Messages | {results['total_system_messages']:,} |
| Avg Messages/Conversation | {results['avg_messages_per_conversation']:.1f} |
"""
        self.write_output(output)

        return results
