"""Base class for all analysis strategies."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Strategy(ABC):
    """Base class for conversation analysis strategies."""

    # Subclasses should override these
    name: str = "base"
    description: str = "Base strategy"

    def __init__(self, conversations_dir: Path, output_dir: Path):
        self.conversations_dir = conversations_dir
        self.output_dir = output_dir

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """
        Run the analysis strategy.

        Returns:
            A dict with results that will also be written to the output file.
        """
        pass

    def get_conversation_files(self) -> list[Path]:
        """Get all JSON conversation files."""
        return sorted(self.conversations_dir.glob("*.json"))

    def write_output(self, content: str, filename: str | None = None) -> Path:
        """Write output to a file in the output directory."""
        if filename is None:
            filename = f"{self.name}.md"
        output_path = self.output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        return output_path
