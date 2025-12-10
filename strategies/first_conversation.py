"""Strategy for finding the first conversation ever."""

import json
from datetime import datetime
from typing import Any

from .base import Strategy


class FirstConversationStrategy(Strategy):
    """Find and display the very first conversation."""

    name = "first_conversation"
    description = "Show your first ChatGPT conversation"

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        # Find conversation with earliest message
        earliest_time = None
        earliest_file = None
        earliest_data = None

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Find earliest timestamp in this conversation
                mapping = data.get("mapping", {})
                for node in mapping.values():
                    message = node.get("message")
                    if message is None:
                        continue

                    create_time = message.get("create_time")
                    if create_time and create_time > 0:
                        if earliest_time is None or create_time < earliest_time:
                            earliest_time = create_time
                            earliest_file = file_path
                            earliest_data = data

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        if earliest_data is None:
            self.write_output("# First Conversation\n\nNo conversations found.")
            return {"error": "No conversations"}

        # Extract messages from the earliest conversation
        mapping = earliest_data.get("mapping", {})
        messages = []

        for node in mapping.values():
            message = node.get("message")
            if message is None:
                continue

            # Skip hidden messages
            metadata = message.get("metadata", {})
            if metadata.get("is_visually_hidden_from_conversation"):
                continue

            create_time = message.get("create_time")
            if not create_time or create_time <= 0:
                continue

            author = message.get("author", {})
            role = author.get("role", "")

            if role not in ("user", "assistant"):
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
                messages.append({
                    "time": create_time,
                    "role": role,
                    "text": text.strip(),
                })

        if not messages:
            self.write_output("# First Conversation\n\nNo messages found in earliest conversation.")
            return {"error": "No messages"}

        # Sort by time
        messages.sort(key=lambda m: m["time"])

        # Find first user message and first assistant reply
        first_user = None
        first_assistant = None

        for msg in messages:
            if msg["role"] == "user" and first_user is None:
                first_user = msg
            elif msg["role"] == "assistant" and first_assistant is None and first_user is not None:
                first_assistant = msg
            if first_user and first_assistant:
                break

        # Calculate conversation stats
        start_time = datetime.fromtimestamp(messages[0]["time"])
        end_time = datetime.fromtimestamp(messages[-1]["time"])
        duration = end_time - start_time
        duration_minutes = duration.total_seconds() / 60
        message_count = len(messages)

        # Build output
        output_lines = ["# Your First ChatGPT Conversation\n"]
        output_lines.append(f"**Date:** {start_time.strftime('%B %d, %Y at %I:%M %p')}\n")

        # Show first 10 messages
        output_lines.append("---\n")
        for msg in messages[:10]:
            role_label = "**You:**" if msg["role"] == "user" else "**ChatGPT:**"
            # Truncate if very long
            text = msg["text"]
            if len(text) > 500:
                text = text[:500] + "…"
            # Escape any > at start of lines to avoid markdown issues
            text = text.replace("\n>", "\n\\>")
            output_lines.append(f"{role_label}\n> {text}\n")

        if len(messages) > 10:
            output_lines.append(f"*...and {len(messages) - 10} more messages*\n")

        output_lines.append("---\n")

        if duration_minutes < 1:
            duration_str = f"{duration.total_seconds():.0f} seconds"
        elif duration_minutes < 60:
            duration_str = f"{duration_minutes:.0f} minutes"
        else:
            hours = duration_minutes / 60
            duration_str = f"{hours:.1f} hours"

        output_lines.append(f"Your first conversation lasted **{duration_str}** and consisted of **{message_count}** messages.")

        self.write_output("\n".join(output_lines))

        return {
            "first_message_date": start_time.isoformat(),
            "duration_minutes": duration_minutes,
            "message_count": message_count,
        }
