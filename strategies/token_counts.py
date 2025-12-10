"""Strategy for counting tokens using tiktoken.

Outputs raw values - comparison selection and formatting is done client-side in charts.js
"""

from typing import Any

import tiktoken

from .base import Strategy


class TokenCountsStrategy(Strategy):
    """Count total tokens across all conversations."""

    name = "token_counts"
    description = "Count total tokens using tiktoken"
    output_key = "static.perspective"

    # Famous long books for comparison (name, word count)
    # Sources: brokebybooks.com, wordsrated.com, wordcounttool.com
    FAMOUS_BOOKS = [
        {"name": "War & Peace", "words": 587_000},
        {"name": "Harry Potter septology", "words": 1_084_000},
        {"name": "Game of Thrones pentology", "words": 1_770_000},
        {"name": "Lord of the Rings trilogy", "words": 455_000},
        {"name": "Les Misérables", "words": 560_000},
        {"name": "Stephen King's IT", "words": 444_000},
        {"name": "Atlas Shrugged", "words": 645_000},
        {"name": "Infinite Jest", "words": 544_000},
    ]

    # Energy comparisons (kwh reference, plural, singular)
    # Energy: ~18 Wh per 1K tokens (GPT-5 scale models, 2025)
    # Source: University of Rhode Island AI Lab (2025), via Tom's Hardware
    ENERGY_COMPARISONS = [
        {"name": "inflatable waving tube man hours", "singular": "inflatable waving tube man hour", "kwh": 0.15},
        {"name": "Christmas light display nights", "singular": "Christmas light display night", "kwh": 3.0},
        {"name": "hours of disco ball spinning", "singular": "hour of disco ball spinning", "kwh": 0.05},
        {"name": "lava lamp meditation sessions", "singular": "lava lamp meditation session", "kwh": 0.12},
        {"name": "DeLorean time travels", "singular": "DeLorean time travel", "kwh": 30000},
        {"name": "lightning bolts", "singular": "lightning bolt", "kwh": 1400},
        {"name": "toaster strudel preparations", "singular": "toaster strudel preparation", "kwh": 0.5},
        {"name": "moments of existential dread", "singular": "moment of existential dread", "kwh": 0.02},
        {"name": "ISS orbits", "singular": "ISS orbit", "kwh": 2500},
        {"name": "robot vacuum sessions", "singular": "robot vacuum session", "kwh": 0.3},
    ]

    # Water comparisons (ml reference, plural, singular)
    # Water: 1.8 L per kWh (industry average WUE)
    # Sources: EESI, Dgtl Infra, Sunbird DCIM
    WATER_COMPARISONS = [
        {"name": "golden retriever baths", "singular": "golden retriever bath", "ml": 40000},
        {"name": "kiddie pools", "singular": "kiddie pool", "ml": 100000},
        {"name": "fishbowls", "singular": "fishbowl", "ml": 5000},
        {"name": "batches of Jell-O", "singular": "batch of Jell-O", "ml": 2000},
        {"name": "hot tub fills", "singular": "hot tub fill", "ml": 150000},
        {"name": "beer kegs", "singular": "beer keg", "ml": 58670},
        {"name": "wine bottles", "singular": "wine bottle", "ml": 750},
        {"name": "fire hydrant blasts", "singular": "fire hydrant blast", "ml": 200000},
        {"name": "snow globe refills", "singular": "snow globe refill", "ml": 4000},
        {"name": "penguin enclosure cleanings", "singular": "penguin enclosure cleaning", "ml": 50000},
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

        # Output raw values + comparison data for client-side rendering
        return {
            "totalWords": total_words,
            "totalTokens": total_tokens,
            "books": self.FAMOUS_BOOKS,
            "energyComparisons": self.ENERGY_COMPARISONS,
            "waterComparisons": self.WATER_COMPARISONS,
        }
