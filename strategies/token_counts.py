"""Strategy for counting tokens using tiktoken."""

import json
from pathlib import Path
from typing import Any

import tiktoken

from .base import Strategy


def format_smart_number(n: float) -> str:
    """
    Format a number smartly:
    - If n >= 1: show integer + 1 decimal, but if decimal < 0.5, just show integer
    - If n < 1: show first non-zero digit after decimal
    - Never show trailing zeros that don't add information
    """
    if n <= 0:
        return "0"

    if n >= 1:
        integer_part = int(n)
        if integer_part > 10:  # Above 10, drop fraction altogether
            return str(integer_part)
        return f"{n:.1f}".rstrip('0').rstrip('.')
    else:
        # n < 1, find first non-zero digit
        # Count how many zeros after decimal point
        if n >= 0.1:
            return f"{n:.1f}".rstrip('0').rstrip('.')
        elif n >= 0.01:
            return f"{n:.2f}".rstrip('0').rstrip('.')
        elif n >= 0.001:
            return f"{n:.3f}".rstrip('0').rstrip('.')
        elif n >= 0.0001:
            return f"{n:.4f}".rstrip('0').rstrip('.')
        elif n >= 0.00001:
            return f"{n:.5f}".rstrip('0').rstrip('.')
        else:
            return f"{n:.6f}".rstrip('0').rstrip('.')


class TokenCountsStrategy(Strategy):
    """Count total tokens across all conversations."""

    name = "token_counts"
    description = "Count total tokens using tiktoken"

    # Energy consumption estimates (2024-2025 research)
    # Based on Epoch AI and OpenAI data: ~0.3 Wh per 500 output tokens for GPT-4o
    # Source: https://epoch.ai/gradient-updates/how-much-energy-does-chatgpt-use
    # Using 0.0006 Wh per token as middle estimate
    WH_PER_TOKEN = 0.0006  # Watt-hours per token

    # Water consumption estimates (2024-2025 research)
    # Based on UC Riverside research: ~21.5 mL per 300-token response (including electricity generation)
    # Source: https://arxiv.org/pdf/2304.03271
    # Using 0.07 mL per token (total water footprint including cooling + electricity generation)
    ML_WATER_PER_TOKEN = 0.07  # milliliters per token

    def run(self) -> dict[str, Any]:
        # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")

        files = self.get_conversation_files()

        total_tokens = 0
        user_tokens = 0
        assistant_tokens = 0
        conversations_processed = 0

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                conversations_processed += 1

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

                    author = message.get("author", {})
                    role = author.get("role", "")

                    if role == "user":
                        user_tokens += tokens
                    elif role == "assistant":
                        assistant_tokens += tokens

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        # Calculate energy and water consumption
        total_wh = total_tokens * self.WH_PER_TOKEN
        total_kwh = total_wh / 1000
        total_water_ml = total_tokens * self.ML_WATER_PER_TOKEN
        total_water_liters = total_water_ml / 1000

        results = {
            "total_tokens": total_tokens,
            "user_tokens": user_tokens,
            "assistant_tokens": assistant_tokens,
            "conversations_processed": conversations_processed,
            "avg_tokens_per_conversation": (
                total_tokens / conversations_processed
                if conversations_processed > 0
                else 0
            ),
            "total_kwh": total_kwh,
            "total_water_liters": total_water_liters,
        }

        # Estimate costs (rough GPT-4 pricing: $0.03/1K input, $0.06/1K output)
        estimated_input_cost = (user_tokens / 1000) * 0.03
        estimated_output_cost = (assistant_tokens / 1000) * 0.06
        estimated_total_cost = estimated_input_cost + estimated_output_cost

        # Build electricity comparisons
        electricity_comparisons = self._get_electricity_comparisons(total_kwh)
        water_comparisons = self._get_water_comparisons(total_water_liters)

        output = f"""# Token Counts

## Summary

| Metric | Count |
|--------|-------|
| Total Tokens | {results['total_tokens']:,} |
| User Tokens | {results['user_tokens']:,} |
| Assistant Tokens | {results['assistant_tokens']:,} |
| Avg Tokens/Conversation | {results['avg_tokens_per_conversation']:,.0f} |

## Estimated Costs (GPT-4 pricing)

| Category | Estimated Cost |
|----------|----------------|
| Input (user) | ${estimated_input_cost:,.2f} |
| Output (assistant) | ${estimated_output_cost:,.2f} |
| **Total** | **${estimated_total_cost:,.2f}** |

*Note: Based on GPT-4 pricing ($0.03/1K input, $0.06/1K output)*

---

## Environmental Impact

### Electricity Consumption

**Estimated total:** {total_kwh:,.2f} kWh ({total_wh:,.0f} Wh)

Based on ~0.3 Wh per 500 tokens (GPT-4o level inference), per [Epoch AI research](https://epoch.ai/gradient-updates/how-much-energy-does-chatgpt-use) and [OpenAI's 2024 disclosure](https://openai.com).

#### How much is {total_kwh:,.2f} kWh? Here's some context:

{electricity_comparisons}

### Water Consumption

**Estimated total:** {total_water_liters:,.1f} liters ({total_water_ml:,.0f} mL)

Based on ~21.5 mL per 300-token response (including data center cooling + water used in electricity generation), per [UC Riverside research](https://arxiv.org/pdf/2304.03271).

#### How much is {total_water_liters:,.1f} liters? Here's some context:

{water_comparisons}

---

### Methodology Notes

- **Electricity estimate:** Uses 0.0006 Wh/token based on Epoch AI's 2025 analysis of GPT-4o inference on H100 hardware. This includes GPU compute but may underestimate total data center overhead (cooling, networking, storage). Actual consumption could be 2-3x higher.

- **Water estimate:** Uses 0.07 mL/token based on UC Riverside's 2023-2024 research. This includes both direct cooling water (Scope 1) and water used in electricity generation (Scope 2). Does not include manufacturing water (Scope 3).

- **Important caveat:** These are rough estimates. Actual consumption varies significantly based on model size, hardware generation, data center efficiency (PUE), geographic location, and cooling technology. Early estimates (e.g., the commonly cited "3 Wh per query") have been revised down ~10x as hardware and software improved.
"""
        self.write_output(output)

        return results

    def _get_electricity_comparisons(self, kwh: float) -> str:
        """Generate bizarre and entertaining electricity comparisons."""
        import random

        comparisons = []

        # Buckets from tiny to massive, each with 5 bizarre comparisons
        # Format: (kwh_value, description_template) - use {n} as placeholder
        buckets = [
            # Tiny (0.001 - 0.05 kWh)
            [
                (0.005, "powering a Tamagotchi for {n} days"),
                (0.01, "charging {n} electric toothbrushes"),
                (0.008, "running a lava lamp for {n} hours"),
                (0.003, "powering {n} singing birthday cards"),
                (0.015, "keeping a nightlight on for {n} nights"),
            ],
            # Small (0.05 - 0.5 kWh)
            [
                (0.1, "powering {n} hours of an inflatable wacky waving arm flailing tube man"),
                (0.2, "running a karaoke machine for {n} drunken hours"),
                (0.15, "operating a cotton candy machine for {n} carnival hours"),
                (0.08, "charging {n} Nintendo Switch sessions"),
                (0.25, "powering a margarita blender for {n} frozen cocktails"),
            ],
            # Medium (0.5 - 5 kWh)
            [
                (1.0, "running a hot tub for {n} romantic hours"),
                (2.0, "powering a home tanning bed for {n} sessions of questionable life choices"),
                (0.8, "operating a popcorn machine for {n} movie nights"),
                (1.5, "running a fog machine for {n} hours of spooky atmosphere"),
                (3.0, "powering a full Christmas light display for {n} festive nights"),
            ],
            # Large (5 - 50 kWh)
            [
                (10, "charging {n} electric scooters from 'borrowed' to full"),
                (25, "powering a roadside 'OPEN' neon sign for {n} days"),
                (15, "running a soft-serve ice cream machine for {n} hours of brain freeze"),
                (30, "operating a car wash for {n} sparkly vehicles"),
                (20, "powering a bouncy castle for {n} birthday parties"),
            ],
            # Huge (50+ kWh)
            [
                (100, "powering a small roller coaster for {n} thrilling hours"),
                (500, "running a movie theater's projector for {n} feature films"),
                (1000, "keeping a walk-in freezer cold for {n} days of ice cream preservation"),
                (10500, "powering an average US home for {n} years"),
                (50000, "running a billboard in Times Square for {n} attention-seeking days"),
            ],
        ]

        comparisons.append("| Your Usage Equals |")
        comparisons.append("|-------------------|")

        for bucket in buckets:
            # Pick one random comparison from each bucket
            ref_kwh, template = random.choice(bucket)
            ratio = kwh / ref_kwh
            if ratio >= 0.001:  # Only show if meaningful
                formatted_num = format_smart_number(ratio)
                description = template.format(n=formatted_num)
                comparisons.append(f"| {description} |")

        return "\n".join(comparisons)

    def _get_water_comparisons(self, liters: float) -> str:
        """Generate bizarre and entertaining water comparisons."""
        import random

        comparisons = []

        # Buckets from tiny to massive, each with 5 bizarre comparisons
        # Format: (liters_value, description_template) - use {n} as placeholder
        buckets = [
            # Tiny (0.01 - 1 liter)
            [
                (0.25, "filling {n} shot glasses for a very hydrated party"),
                (0.5, "making {n} cups of instant ramen (the college student unit)"),
                (0.35, "filling {n} hamster water bottles"),
                (0.1, "producing {n} tears while watching sad movies"),
                (0.75, "brewing {n} cups of pour-over coffee for insufferable hipsters"),
            ],
            # Small (1 - 20 liters)
            [
                (5, "filling {n} fishbowls for your new emotional support goldfish"),
                (2, "making {n} batches of Jell-O (the jiggly unit)"),
                (10, "filling {n} Super Soakers for backyard warfare"),
                (3, "watering {n} sad office plants back to life"),
                (8, "making {n} buckets of water balloons for ultimate betrayal"),
            ],
            # Medium (20 - 200 liters)
            [
                (60, "taking {n} showers (the guilt-free length, not the concert prep)"),
                (40, "giving {n} baths to a very dirty golden retriever"),
                (100, "filling {n} kiddie pools for tiny humans"),
                (150, "making {n} bathtubs worth of bubble bath"),
                (80, "running {n} loads through a pressure washer for that satisfying clean"),
            ],
            # Large (200 - 2000 liters)
            [
                (500, "filling {n} hot tubs for awkward networking events"),
                (1000, "supplying {n} days of water for a small elephant"),
                (750, "making {n} massive slip-n-slides"),
                (300, "filling {n} restaurant-grade ice machines"),
                (400, "producing {n} failed attempts at a backyard ice rink"),
            ],
            # Huge (2000+ liters)
            [
                (5000, "filling {n} above-ground pools for suburban flex"),
                (10000, "keeping {n} dolphins hydrated for a day"),
                (50000, "flooding {n} movie sets for an action sequence"),
                (100000, "filling {n} Olympic diving pools"),
                (73000, "supplying an average US household for {n} years"),
            ],
        ]

        comparisons.append("| Your Usage Equals |")
        comparisons.append("|-------------------|")

        for bucket in buckets:
            # Pick one random comparison from each bucket
            ref_liters, template = random.choice(bucket)
            ratio = liters / ref_liters
            if ratio >= 0.001:  # Only show if meaningful
                formatted_num = format_smart_number(ratio)
                description = template.format(n=formatted_num)
                comparisons.append(f"| {description} |")

        return "\n".join(comparisons)
