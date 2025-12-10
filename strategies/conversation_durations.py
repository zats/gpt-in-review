"""Strategy for analyzing conversation durations."""

from typing import Any

from .base import Strategy


class ConversationDurationsStrategy(Strategy):
    """Find the longest conversation by time span."""

    name = "conversation_durations"
    description = "Find longest running conversation"
    output_key = "static.longestConversation"

    def run(self) -> dict[str, Any]:
        conversations_data = []

        for data in self.conversations:
            title = data.get("title") or "Untitled"

            # Get all message timestamps
            message_times = []
            mapping = data.get("mapping", {})
            for node in mapping.values():
                message = node.get("message")
                if message is None:
                    continue
                msg_time = message.get("create_time")
                if msg_time and msg_time > 0:
                    message_times.append(msg_time)

            if not message_times:
                continue

            first_msg = min(message_times)
            last_msg = max(message_times)
            duration_seconds = last_msg - first_msg

            conversations_data.append({
                "title": title,
                "duration_seconds": duration_seconds,
            })

        if not conversations_data:
            return {"value": "", "title": ""}

        # Find longest by duration
        longest = max(conversations_data, key=lambda x: x["duration_seconds"])

        # Format duration
        duration_seconds = longest["duration_seconds"]
        if duration_seconds < 60:
            value = f"{duration_seconds:.0f} seconds"
        elif duration_seconds < 3600:
            value = f"{duration_seconds / 60:.1f} minutes"
        elif duration_seconds < 86400:
            value = f"{duration_seconds / 3600:.1f} hours"
        else:
            value = f"{duration_seconds / 86400:.1f} days"

        return {
            "value": value,
            "title": longest["title"],
        }
