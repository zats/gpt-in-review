"""Strategy for finding abandoned conversations."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import Strategy


class AbandonedConversationsStrategy(Strategy):
    """Find conversations that were started but abandoned."""

    name = "abandoned_conversations"
    description = "Find conversations abandoned before getting a response"

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        # Categories of abandonment
        no_response = []  # User sent message, no assistant response
        empty_response = []  # Assistant responded with empty/minimal content
        single_exchange_abandoned = []  # Got response but never followed up (very short)

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                title = data.get("title") or "Untitled"
                create_time = data.get("create_time")

                # Build message chain from mapping
                mapping = data.get("mapping", {})

                # Collect messages by role
                user_messages = []
                assistant_messages = []

                for node in mapping.values():
                    message = node.get("message")
                    if message is None:
                        continue

                    # Skip hidden system messages
                    metadata = message.get("metadata", {})
                    if metadata.get("is_visually_hidden_from_conversation"):
                        continue

                    author = message.get("author", {})
                    role = author.get("role", "")

                    content = message.get("content", {})
                    parts = content.get("parts", [])
                    text = ""
                    for part in parts:
                        if isinstance(part, str):
                            text += part

                    msg_time = message.get("create_time")

                    if role == "user" and text.strip():
                        user_messages.append({
                            "text": text,
                            "time": msg_time,
                        })
                    elif role == "assistant":
                        assistant_messages.append({
                            "text": text,
                            "time": msg_time,
                        })

                # Get first user message text for display
                first_user_msg = user_messages[0]["text"][:100] if user_messages else ""

                conv_info = {
                    "title": title,
                    "filename": file_path.name,
                    "create_time": create_time,
                    "first_message": first_user_msg,
                    "user_count": len(user_messages),
                    "assistant_count": len(assistant_messages),
                }

                # Case 1: User sent message(s) but got no assistant response at all
                if user_messages and not assistant_messages:
                    no_response.append(conv_info)
                    continue

                # Case 2: Assistant responded but ALL responses are empty/minimal
                # (This catches cases where tool calls exist but no actual text response)
                if assistant_messages:
                    # Check if ANY assistant message has substantial text
                    has_real_response = any(
                        len(msg["text"].strip()) >= 10 for msg in assistant_messages
                    )
                    if not has_real_response:
                        # Get the longest response to show
                        longest = max(assistant_messages, key=lambda m: len(m["text"]))
                        conv_info["assistant_response"] = longest["text"][:50].strip() if longest["text"].strip() else "(empty)"
                        empty_response.append(conv_info)

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        def format_timestamp(ts: float | None) -> str:
            if ts is None:
                return "unknown"
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

        # Build output
        output_lines = ["# Abandoned Conversations\n"]

        # No response section
        output_lines.append(f"## No Response Received ({len(no_response)} conversations)\n")
        output_lines.append("Conversations where you sent a message but never got a response.\n")

        if no_response:
            output_lines.append("| Date | Title | First Message |")
            output_lines.append("|------|-------|---------------|")
            for c in sorted(no_response, key=lambda x: x["create_time"] or 0, reverse=True)[:50]:
                first_msg = c["first_message"].replace("|", "\\|").replace("\n", " ")[:60]
                output_lines.append(
                    f"| {format_timestamp(c['create_time'])} | {c['title'][:30]} | {first_msg}... |"
                )
            if len(no_response) > 50:
                output_lines.append(f"\n*...and {len(no_response) - 50} more*\n")
        else:
            output_lines.append("*None found*\n")

        # Empty response section
        output_lines.append(f"\n## Empty/Minimal Response ({len(empty_response)} conversations)\n")
        output_lines.append("Conversations where the assistant's first response was empty or very short.\n")

        if empty_response:
            output_lines.append("| Date | Title | Response |")
            output_lines.append("|------|-------|----------|")
            for c in sorted(empty_response, key=lambda x: x["create_time"] or 0, reverse=True)[:50]:
                resp = c.get("assistant_response", "").replace("|", "\\|").replace("\n", " ")
                output_lines.append(
                    f"| {format_timestamp(c['create_time'])} | {c['title'][:30]} | {resp} |"
                )
            if len(empty_response) > 50:
                output_lines.append(f"\n*...and {len(empty_response) - 50} more*\n")
        else:
            output_lines.append("*None found*\n")

        # Summary
        output_lines.append("\n## Summary\n")
        total_abandoned = len(no_response) + len(empty_response)
        output_lines.append(f"- **No response:** {len(no_response)}")
        output_lines.append(f"- **Empty response:** {len(empty_response)}")
        output_lines.append(f"- **Total abandoned:** {total_abandoned}")

        self.write_output("\n".join(output_lines))

        return {
            "no_response_count": len(no_response),
            "empty_response_count": len(empty_response),
            "total_abandoned": total_abandoned,
        }
