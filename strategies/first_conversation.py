"""Strategy for finding the first conversation ever."""

from datetime import datetime
from typing import Any

from .base import Strategy


class FirstConversationStrategy(Strategy):
    """Find and display the very first conversation."""

    name = "first_conversation"
    description = "Show your first ChatGPT conversation"
    output_key = "static.firstConversation"

    def run(self) -> dict[str, Any]:
        # Find conversation with earliest message
        earliest_time = None
        earliest_data = None

        for data in self.conversations:
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
                        earliest_data = data

        if earliest_data is None:
            return {"date": "", "duration": "", "messages": []}

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
            return {"date": "", "duration": "", "messages": []}

        # Sort by time
        messages.sort(key=lambda m: m["time"])

        # Calculate conversation stats
        start_time = datetime.fromtimestamp(messages[0]["time"])
        end_time = datetime.fromtimestamp(messages[-1]["time"])
        duration = end_time - start_time
        duration_minutes = duration.total_seconds() / 60

        # Format duration
        if duration_minutes < 1:
            duration_str = f"{int(duration.total_seconds())} seconds"
        elif duration_minutes < 60:
            duration_str = f"{int(duration_minutes)} minute{'s' if int(duration_minutes) != 1 else ''}"
        else:
            hours = duration_minutes / 60
            duration_str = f"{hours:.1f} hours"

        # Build message list for output (first few messages, truncated)
        output_messages = []
        for msg in messages[:4]:  # First 4 messages
            text = msg["text"]
            if len(text) > 200:
                text = text[:200] + "..."
            output_messages.append({
                "role": msg["role"],
                "text": text,
            })

        return {
            "date": start_time.strftime("%B %d, %Y"),
            "duration": duration_str,
            "messages": output_messages,
        }
