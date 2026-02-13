"""Base parser interface."""
from abc import ABC, abstractmethod
from pathlib import Path
from vast_rag.types import ParsedDocument


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document and return structured content.

        Args:
            file_path: Path to the document file

        Returns:
            ParsedDocument with extracted text and metadata

        Raises:
            ValueError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if this parser can handle the file
        """
        pass
