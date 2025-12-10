"""Strategy for generating a fake OpenAI-style API key."""

import random
import string
from typing import Any

from .base import Strategy


class ApiKeyStrategy(Strategy):
    """Generate a fake OpenAI-looking API key for fun."""

    name = "api_key"
    description = "Generate a fake OpenAI-style API key"
    output_key = "apiKey"

    # Character set: alphanumeric (OpenAI keys use base62-like encoding)
    CHARS = string.ascii_letters + string.digits

    def run(self) -> dict[str, Any]:
        # Format: sk-proj-{segment}-{short}_{segment}_{segment}-{segment}_{segment}-{segment}
        # Mimics real OpenAI project key structure with - and _ breaks
        key = "sk-proj-"
        key += self._segment(25)
        key += "-"
        key += self._segment(1, 2)
        key += "_"
        key += self._segment(40, 45)
        key += "_"
        key += self._segment(12, 16)
        key += "-"
        key += self._segment(20, 26)
        key += "_"
        key += self._segment(10, 14)
        key += "-"
        key += self._segment(28, 34)

        return {"key": key}

    def _segment(self, min_len: int, max_len: int = None) -> str:
        """Generate a random alphanumeric segment."""
        length = min_len if max_len is None else random.randint(min_len, max_len)
        return "".join(random.choice(self.CHARS) for _ in range(length))
