"""Strategy for finding the longest assistant response."""

from typing import Any

from .base import Strategy


class ResponseLengthsStrategy(Strategy):
    """Find the longest assistant response by character count."""

    name = "response_lengths"
    description = "Find longest assistant text response"
    output_key = "static.longestMessage"

    def run(self) -> dict[str, Any]:
        longest_response = None
        longest_length = 0
        longest_title = ""

        for data in self.conversations:
            title = data.get("title") or "Untitled"
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

                if len(text) > longest_length:
                    longest_length = len(text)
                    longest_response = text
                    longest_title = title

        if longest_response is None:
            return {"value": "", "title": ""}

        # Format the value with thousands separator
        return {
            "value": f"{longest_length:,}",
            "title": longest_title,
        }
