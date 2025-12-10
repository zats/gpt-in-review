"""Strategy for estimating printed page count (CVS receipt comparison)."""

import random
from typing import Any

from .base import Strategy


class PageCountStrategy(Strategy):
    """Estimate CVS receipt length for perspective section."""

    name = "page_count"
    description = "Estimate CVS receipt length"
    output_key = "static.perspective"

    LINES_PER_PAGE = 50

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
        receipt_length_feet = total_lines / 40

        # Get comparison
        cvs_note = self._get_receipt_comparison(receipt_length_feet)

        return {
            "cvsReceipt": f"{receipt_length_feet:,.0f}",
            "cvsNote": cvs_note,
        }

    def _get_receipt_comparison(self, feet: float) -> str:
        """Return a fun comparison for CVS receipt length (randomly selected each run)."""
        # (reference length in feet, name, emoji/description)
        comparisons = [
            (8981, "Golden Gate Bridge"),
            (1063, "Eiffel Tower (height)"),
            (1454, "Empire State Building (height)"),
            (5280, "mile"),
            (300, "football field"),
            (100, "blue whale"),
            (555, "Washington Monument"),
            (630, "St. Louis Arch"),
            (2717, "Burj Khalifa (height)"),
            (60, "bowling lane"),
            (90, "basketball court"),
            (360, "Statue of Liberty (with pedestal)"),
            (1250, "average city block"),
            (27, "school bus"),
            (50, "semi truck"),
        ]

        ref_feet, name = random.choice(comparisons)
        ratio = feet / ref_feet

        if ratio < 0.1:
            return "A modest CVS run"
        elif ratio < 1:
            return f"{ratio:.1f}× {name}"
        elif ratio < 2:
            return f"{ratio:.1f}× {name}"
        elif ratio < 10:
            return f"{ratio:.0f}× {name}"
        else:
            return f"{ratio:.0f}× {name}"
