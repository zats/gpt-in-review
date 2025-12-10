"""Strategy for counting tokens using tiktoken."""

import random
from typing import Any

import tiktoken

from .base import Strategy


class TokenCountsStrategy(Strategy):
    """Count total tokens across all conversations."""

    name = "token_counts"
    description = "Count total tokens using tiktoken"
    output_key = "static.perspective"

    # Energy: ~18 Wh per 1K tokens (GPT-5 scale models, 2025)
    # Source: University of Rhode Island AI Lab (2025), via Tom's Hardware
    #         "medium-length 1,000-token GPT-5 response averages 18.35 Wh"
    WH_PER_TOKEN = 0.018

    # Water: 1.8 L per kWh (industry average WUE)
    # Sources: EESI "Data Centers and Water Consumption" (eesi.org)
    #          Dgtl Infra "Data Center Water Usage" (dgtlinfra.com)
    #          Sunbird DCIM "What Is Water Usage Effectiveness" (sunbirddcim.com)
    L_WATER_PER_KWH = 1.8

    # Famous long books for comparison (name, word count)
    # Sources: brokebybooks.com, wordsrated.com, wordcounttool.com
    FAMOUS_BOOKS = [
        ("War & Peace", 587_000),
        ("Harry Potter (all 7)", 1_084_000),
        ("A Song of Ice & Fire (5 books)", 1_770_000),
        ("Lord of the Rings trilogy", 455_000),
        ("Les Misérables", 560_000),
        ("Don Quixote", 350_000),
        ("Stephen King's IT", 444_000),
        ("Atlas Shrugged", 645_000),
        ("Infinite Jest", 544_000),
    ]

    def run(self) -> dict[str, Any]:
        # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")

        total_tokens = 0
        total_words = 0

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

                text = ""
                for part in parts:
                    if isinstance(part, str):
                        text += part

                if not text:
                    continue

                tokens = len(encoding.encode(text))
                total_tokens += tokens
                total_words += len(text.split())

        # Calculate energy and water consumption
        total_wh = total_tokens * self.WH_PER_TOKEN
        total_kwh = total_wh / 1000
        total_water_l = total_kwh * self.L_WATER_PER_KWH
        total_water_ml = total_water_l * 1000  # for fun comparisons

        # Book pages (assuming ~250 words per page)
        book_pages = total_words / 250

        # Get fun comparisons
        energy_fun = self._get_energy_comparison(total_wh)
        water_fun = self._get_water_comparison(total_water_ml)

        # Get book comparison (randomly selected)
        book_name, book_ratio, book_words = self._get_book_comparison(total_words)

        # Format for data.json
        return {
            "totalWords": self._format_millions(total_words),
            "bookPages": f"{book_pages:,.0f}",
            "bookName": book_name,
            "bookRatio": f"{book_ratio:.2f}x",
            "bookWords": f"~{book_words:,} words each",
            "tokens": self._format_millions(total_tokens),
            "energy": f"{total_kwh:.2f}",  # kWh
            "energyFun": energy_fun,
            "water": f"{total_water_l:.2f}",  # liters
            "waterFun": water_fun,
        }

    def _format_millions(self, n: int) -> str:
        """Format large numbers with M suffix."""
        if n >= 1_000_000:
            return f"{n / 1_000_000:.2f}M"
        elif n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)

    def _get_book_comparison(self, total_words: int) -> tuple[str, float, int]:
        """Get a random famous book comparison."""
        book_name, book_words = random.choice(self.FAMOUS_BOOKS)
        ratio = total_words / book_words
        return book_name, ratio, book_words

    def _get_energy_comparison(self, wh: float) -> str:
        """Get a fun energy comparison (randomly selected each run)."""
        # (kWh reference, plural form, singular form)
        comparisons = [
            (0.2, "hours of karaoke machine", "hour of karaoke machine"),
            (1.0, "hot tub hours", "hot tub hour"),
            (0.8, "popcorn machine movie nights", "popcorn machine movie night"),
            (0.15, "inflatable waving tube man hours", "inflatable waving tube man hour"),
            (3.0, "Christmas light display nights", "Christmas light display night"),
            (0.05, "hours of disco ball spinning", "hour of disco ball spinning"),
            (0.5, "hours of electric blanket coziness", "hour of electric blanket coziness"),
            (0.12, "lava lamp meditation sessions", "lava lamp meditation session"),
            (0.03, "phone charges", "phone charge"),
            (1.5, "hours of space heater warmth", "hour of space heater warmth"),
            (0.06, "hours of fairy lights twinkling", "hour of fairy lights twinkling"),
            (0.4, "loads of laundry", "load of laundry"),
            (0.25, "hours of gaming console", "hour of gaming console"),
            (2.0, "hours of air conditioning", "hour of air conditioning"),
            (0.08, "hours of desk fan breeze", "hour of desk fan breeze"),
        ]

        ref_kwh, plural, singular = random.choice(comparisons)
        ref_wh = ref_kwh * 1000
        ratio = wh / ref_wh

        if ratio < 1:
            return f"{ratio:.1f} {singular}"
        elif ratio < 2:
            return f"{ratio:.1f} {plural}"
        else:
            return f"{ratio:.0f} {plural}"

    def _get_water_comparison(self, ml: float) -> str:
        """Get a fun water comparison (randomly selected each run)."""
        # (ml reference, plural form, singular form)
        comparisons = [
            (40000, "golden retriever baths", "golden retriever bath"),
            (60000, "guilt-free showers", "guilt-free shower"),
            (100000, "kiddie pools", "kiddie pool"),
            (5000, "fishbowls", "fishbowl"),
            (2000, "batches of Jell-O", "batch of Jell-O"),
            (250, "glasses of water", "glass of water"),
            (500, "water bottles", "water bottle"),
            (15000, "bubble baths", "bubble bath"),
            (1000, "ice cube trays", "ice cube tray"),
            (350, "cups of coffee (water portion)", "cup of coffee (water portion)"),
            (20000, "loads of dishes", "load of dishes"),
            (3000, "aquarium top-offs", "aquarium top-off"),
            (8000, "toilet flushes", "toilet flush"),
            (150000, "hot tub fills", "hot tub fill"),
            (30000, "car washes", "car wash"),
        ]

        ref_ml, plural, singular = random.choice(comparisons)
        ratio = ml / ref_ml

        if ratio < 1:
            return f"{ratio:.1f} {singular}"
        elif ratio < 2:
            return f"{ratio:.1f} {plural}"
        else:
            return f"{ratio:.0f} {plural}"
