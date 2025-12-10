"""Strategy for analyzing conversation durations."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .base import Strategy


class ConversationDurationsStrategy(Strategy):
    """Analyze conversation durations - shortest, longest, most revisited."""

    name = "conversation_durations"
    description = "Analyze conversation time spans"

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        conversations = []

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                title = data.get("title") or "Untitled"
                create_time = data.get("create_time")
                update_time = data.get("update_time")

                if create_time is None:
                    continue

                # Get all message timestamps
                message_times = []
                mapping = data.get("mapping", {})
                for node in mapping.values():
                    message = node.get("message")
                    if message is None:
                        continue
                    msg_time = message.get("create_time")
                    if msg_time:
                        message_times.append(msg_time)

                if not message_times:
                    continue

                first_msg = min(message_times)
                last_msg = max(message_times)
                duration_seconds = last_msg - first_msg

                conversations.append(
                    {
                        "title": title,
                        "filename": file_path.name,
                        "create_time": create_time,
                        "update_time": update_time or create_time,
                        "first_message": first_msg,
                        "last_message": last_msg,
                        "duration_seconds": duration_seconds,
                        "message_count": len(message_times),
                    }
                )

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        if not conversations:
            self.write_output("# Conversation Durations\n\nNo conversations found.")
            return {"error": "No conversations found"}

        # Sort by duration
        by_duration = sorted(conversations, key=lambda x: x["duration_seconds"])

        # Shortest (excluding 0-duration single-message conversations)
        non_zero = [c for c in by_duration if c["duration_seconds"] > 0]
        shortest = non_zero[:10] if non_zero else by_duration[:10]

        # Longest running (by total time span)
        longest = by_duration[-10:][::-1]

        # Most revisited (large gap between create and update time)
        def format_duration(seconds: float) -> str:
            if seconds < 60:
                return f"{seconds:.0f} seconds"
            elif seconds < 3600:
                return f"{seconds / 60:.1f} minutes"
            elif seconds < 86400:
                return f"{seconds / 3600:.1f} hours"
            else:
                return f"{seconds / 86400:.1f} days"

        def format_timestamp(ts: float) -> str:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

        # Build output
        output_lines = ["# Conversation Durations\n"]

        output_lines.append("## Longest Running Conversations\n")
        output_lines.append(
            "| Duration | Title | Started | Messages |\n|----------|-------|---------|----------|"
        )
        for c in longest:
            output_lines.append(
                f"| {format_duration(c['duration_seconds'])} | {c['title'][:40]} | {format_timestamp(c['first_message'])} | {c['message_count']} |"
            )

        output_lines.append("\n## Shortest Conversations (non-zero duration)\n")
        output_lines.append(
            "| Duration | Title | Started | Messages |\n|----------|-------|---------|----------|"
        )
        for c in shortest[:10]:
            output_lines.append(
                f"| {format_duration(c['duration_seconds'])} | {c['title'][:40]} | {format_timestamp(c['first_message'])} | {c['message_count']} |"
            )

        # Statistics
        durations = [c["duration_seconds"] for c in conversations]
        avg_duration = sum(durations) / len(durations) if durations else 0
        total_time = sum(durations)

        output_lines.append("\n## Statistics\n")
        output_lines.append(f"- **Total conversations:** {len(conversations):,}")
        output_lines.append(f"- **Average duration:** {format_duration(avg_duration)}")
        output_lines.append(
            f"- **Total time spent in conversations:** {format_duration(total_time)}"
        )
        output_lines.append(
            f"- **Longest conversation:** {format_duration(max(durations))}"
        )

        self.write_output("\n".join(output_lines))

        return {
            "total_conversations": len(conversations),
            "avg_duration_seconds": avg_duration,
            "max_duration_seconds": max(durations) if durations else 0,
            "total_time_seconds": total_time,
        }
