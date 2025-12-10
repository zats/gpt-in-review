"""Strategy for estimating printed page count."""

import json
from pathlib import Path
from typing import Any

from .base import Strategy


class PageCountStrategy(Strategy):
    """Estimate how many pages it would take to print all conversations."""

    name = "page_count"
    description = "Estimate printed page count for all conversations"

    # Typical book page: ~250 words or ~1500 characters with spaces
    # A4 page with standard margins: ~3000 characters
    CHARS_PER_PAGE = 3000
    LINES_PER_PAGE = 50  # Approximate lines per page

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        total_chars = 0
        total_lines = 0
        total_words = 0

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

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
                            total_chars += len(part)
                            total_lines += part.count("\n") + 1
                            total_words += len(part.split())

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        pages_by_chars = total_chars / self.CHARS_PER_PAGE
        pages_by_lines = total_lines / self.LINES_PER_PAGE

        # Average the two estimates
        estimated_pages = (pages_by_chars + pages_by_lines) / 2

        results = {
            "total_characters": total_chars,
            "total_lines": total_lines,
            "total_words": total_words,
            "estimated_pages": estimated_pages,
        }

        # Fun comparisons
        avg_book_pages = 300
        books_equivalent = estimated_pages / avg_book_pages

        # Tolstoy's War and Peace is ~580,000 words
        war_and_peace_words = 580000
        war_and_peace_equivalent = total_words / war_and_peace_words

        # Physical dimensions
        # Standard paper thickness: ~0.1mm per sheet (0.05mm per page for double-sided)
        # Using single-sided printing: 0.1mm = 0.00394 inches per page
        stack_height_inches = estimated_pages * 0.00394
        stack_height_feet = stack_height_inches / 12
        stack_height_cm = estimated_pages * 0.01  # 0.1mm = 0.01cm

        # CVS receipt: thermal paper at ~3 inches wide, ~0.5 inch per item line
        # Average ~40 lines per foot of receipt
        # Our pages have ~50 lines, so receipt length = total_lines / 40 feet
        receipt_length_feet = total_lines / 40
        receipt_length_meters = receipt_length_feet * 0.3048

        # Fun height comparisons
        height_comparisons = []
        if stack_height_feet < 1:
            height_comparisons.append(f"a stack **{stack_height_inches:.1f} inches** tall")
        elif stack_height_feet < 6:
            height_comparisons.append(f"a stack **{stack_height_feet:.1f} feet** tall")
            if stack_height_feet > 1:
                height_comparisons.append(f"about as tall as a {self._get_height_comparison(stack_height_feet)}")
        else:
            height_comparisons.append(f"a stack **{stack_height_feet:.1f} feet** ({stack_height_cm / 100:.1f} meters) tall")

        # CVS receipt comparison
        receipt_comparison = self._get_receipt_comparison(receipt_length_feet)

        output = f"""# Page Count Estimate

## Raw Numbers

| Metric | Count |
|--------|-------|
| Total Characters | {total_chars:,} |
| Total Lines | {total_lines:,} |
| Total Words | {total_words:,} |

## Page Estimates

| Method | Pages |
|--------|-------|
| By character count (~3000/page) | {pages_by_chars:,.0f} |
| By line count (~50/page) | {pages_by_lines:,.0f} |
| **Average estimate** | **{estimated_pages:,.0f}** |

## Physical Dimensions

If you printed all your conversations:

| Measurement | Value |
|-------------|-------|
| Stack height | {stack_height_feet:.1f} feet ({stack_height_cm:.0f} cm) |
| CVS receipt length | {receipt_length_feet:.0f} feet ({receipt_length_meters:.0f} meters) |

### Stack Height

Printed single-sided on standard paper, your conversations would form {height_comparisons[0]}.

### CVS Receipt Mode

If printed as one continuous CVS-style receipt, it would stretch **{receipt_length_feet:,.0f} feet** ({receipt_length_meters:,.0f} meters). {receipt_comparison}

## Literary Comparisons

- **Books:** Your conversations would fill **{books_equivalent:.1f}** average-length books (~300 pages each)
- **War and Peace:** You've written **{war_and_peace_equivalent:.2f}x** the length of Tolstoy's War and Peace
- **Daily writing:** At {total_words:,} words, that's the equivalent of writing **{total_words / 365:,.0f} words per day** for a year

*Assuming standard book formatting with preserved whitespace and newlines.*
"""
        self.write_output(output)

        return results

    def _get_height_comparison(self, feet: float) -> str:
        """Return a fun comparison for stack height."""
        if feet < 0.5:
            return "paperback novel"
        elif feet < 1:
            return "thick dictionary"
        elif feet < 1.5:
            return "toddler"
        elif feet < 2.5:
            return "golden retriever sitting down"
        elif feet < 3.5:
            return "kitchen counter"
        elif feet < 4.5:
            return "refrigerator"
        elif feet < 6:
            return "tall person"
        elif feet < 10:
            return "one-story building"
        elif feet < 20:
            return "two-story house"
        else:
            return "telephone pole"

    def _get_receipt_comparison(self, feet: float) -> str:
        """Return a fun comparison for CVS receipt length."""
        if feet < 10:
            return "That's a modest CVS run - maybe just bought gum."
        elif feet < 50:
            return "Now we're talking! That's a proper CVS receipt."
        elif feet < 100:
            return "That's enough receipt to gift wrap a car."
        elif feet < 500:
            return "You could use this as a scarf and still have leftovers."
        elif feet < 1000:
            return "This receipt could wrap around a football field."
        elif feet < 5000:
            return "You'd need a wheelbarrow to carry this receipt out of the store."
        elif feet < 10000:
            return "That's taller than the Statue of Liberty laid on its side."
        elif feet < 15000:
            return "You could span the Golden Gate Bridge 3 times and still have paper left over."
        elif feet < 25000:
            return "That's higher than a skydiver jumps from. Your receipt has literally reached the clouds."
        elif feet < 35000:
            return "Commercial airplanes cruise at this altitude. Your receipt is now a flight hazard."
        elif feet < 50000:
            return "You've passed Mount Everest (29,032 ft). Your receipt needs supplemental oxygen."
        elif feet < 75000:
            return "Weather balloons operate at this height. Your receipt is now doing science."
        elif feet < 100000:
            return "You're in the stratosphere. Fighter jets can barely reach you up here."
        else:
            return "Congratulations, you've achieved CVS receipt immortality. This could reach low Earth orbit."
