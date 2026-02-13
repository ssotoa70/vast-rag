"""Markdown document parser."""
import re
from pathlib import Path
import markdown
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class MarkdownParser(BaseParser):
    """Parser for Markdown documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is markdown."""
        return file_path.suffix.lower() in {".md", ".markdown"}

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse markdown file and extract sections."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: not a markdown file")

        content = file_path.read_text(encoding="utf-8")

        # Extract section headers
        sections = self._extract_sections(content)

        # Convert to plain text (strip markdown syntax)
        text = markdown.markdown(content)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        metadata = {
            "sections": sections,
            "pages": 1,  # Markdown doesn't have pages
            "format": "markdown",
        }

        return ParsedDocument(
            text=text.strip(),
            metadata=metadata,
            format="markdown",
            source_path=file_path,
        )

    def _extract_sections(self, content: str) -> list[str]:
        """Extract section headers from markdown."""
        # Match markdown headers (# Header)
        header_pattern = r'^#{1,6}\s+(.+)$'
        headers = re.findall(header_pattern, content, re.MULTILINE)
        return [h.strip() for h in headers]
