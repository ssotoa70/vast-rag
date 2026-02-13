"""Factory for selecting appropriate document parser."""
import logging
from pathlib import Path
from typing import Type

from vast_rag.parsers.base import BaseParser
from vast_rag.parsers.markdown import MarkdownParser
from vast_rag.parsers.text import TextParser
from vast_rag.parsers.pdf import PDFParser
from vast_rag.parsers.html import HTMLParser
from vast_rag.parsers.docx import DOCXParser
from vast_rag.types import ParsedDocument

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating appropriate document parsers."""

    def __init__(self):
        """Initialize factory with all available parsers."""
        self._parsers: list[Type[BaseParser]] = [
            PDFParser,
            DOCXParser,
            HTMLParser,
            MarkdownParser,
            TextParser,  # Keep text parser last as fallback
        ]

    def get_parser(self, file_path: Path) -> BaseParser:
        """Get appropriate parser for the file.

        Args:
            file_path: Path to the file

        Returns:
            Parser instance that can handle the file

        Raises:
            ValueError: If no parser can handle the file
        """
        for parser_class in self._parsers:
            parser = parser_class()
            if parser.can_parse(file_path):
                logger.debug(f"Selected {parser_class.__name__} for {file_path}")
                return parser

        raise ValueError(
            f"No parser available for {file_path}. "
            f"Supported extensions: .pdf, .docx, .html, .md, .txt, code files"
        )

    def parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse a document using the appropriate parser.

        Args:
            file_path: Path to the document

        Returns:
            ParsedDocument with extracted content

        Raises:
            ValueError: If file cannot be parsed
        """
        parser = self.get_parser(file_path)
        return parser.parse(file_path)
