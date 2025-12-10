"""Strategy for estimating printed page count (CVS receipt comparison).

Outputs raw values - comparison selection and formatting is done client-side in charts.js
"""

from typing import Any

from .base import Strategy


class PageCountStrategy(Strategy):
    """Estimate CVS receipt length for perspective section."""

    name = "page_count"
    description = "Estimate CVS receipt length"
    output_key = "static.perspective"

    LINES_PER_PAGE = 50

    # CVS receipt comparisons (feet, name)
    CVS_COMPARISONS = [
        {"name": "Golden Gate Bridges", "feet": 8981},
        {"name": "Eiffel Towers", "feet": 1063},
        {"name": "Empire State Buildings", "feet": 1454},
        {"name": "blue whales", "feet": 100},
        {"name": "Washington Monuments", "feet": 555},
        {"name": "St. Louis Archs", "feet": 630},
        {"name": "Burj Khalifas", "feet": 2717},
        {"name": "Statue of Liberty (with pedestal)", "feet": 360},
        {"name": "distance to the Moon", "feet": 1261154880},
    ]

    def run(self) -> dict[str, Any]:
        total_lines = 0

        for data in self.conversations:
            mapping = data.get("mapping", {})
            for node in mapping.values():
                message = node.get("message")
                if message is None:
                    continue

                # Skip hidden system messages
                metadata = message.get("metadata", {})
                if metadata.get("is_visually_hidden_from_conversation"):
                    continue

                content = message.get("content", {})
                parts = content.get("parts", [])

                for part in parts:
                    if isinstance(part, str):
                        total_lines += part.count("\n") + 1

        # CVS receipt: ~40 lines per foot
        receipt_length_feet = int(total_lines / 40)

        # Output raw value + comparisons for client-side rendering
        return {
            "cvsReceiptFeet": receipt_length_feet,
            "cvsComparisons": self.CVS_COMPARISONS,
        }
