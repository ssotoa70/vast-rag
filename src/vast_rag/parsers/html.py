"""HTML document parser."""
from pathlib import Path
from bs4 import BeautifulSoup
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class HTMLParser(BaseParser):
    """Parser for HTML documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is HTML."""
        return file_path.suffix.lower() in {".html", ".htm"}

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse HTML and extract text content."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: not an HTML file")

        content = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style tags
        for element in soup(["script", "style"]):
            element.decompose()

        # Extract headings
        sections = []
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            sections.append(heading.get_text(strip=True))

        # Get text content
        text = soup.get_text(separator="\n", strip=True)

        metadata = {
            "sections": sections,
            "pages": 1,
            "format": "html",
        }

        return ParsedDocument(
            text=text,
            metadata=metadata,
            format="html",
            source_path=file_path,
        )
