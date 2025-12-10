"""Base class for all analysis strategies."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Strategy(ABC):
    """Base class for conversation analysis strategies."""

    # Subclasses should override these
    name: str = "base"
    description: str = "Base strategy"

    # The key(s) this strategy contributes to in data.json
    # Can be a single key like "topics" or a nested path like "static.overview"
    output_key: str = ""

    def __init__(self, conversations: list[dict], output_dir: Path):
        """
        Initialize the strategy with conversation data.

        Args:
            conversations: List of conversation dictionaries loaded from conversations.json
            output_dir: Directory for any file outputs (e.g., images)
        """
        self.conversations = conversations
        self.output_dir = output_dir

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """
        Run the analysis strategy.

        Returns:
            A dict with the data to be merged into data.json.
            The structure should match what's expected for this strategy's output_key.
        """
        pass
