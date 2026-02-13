"""Plain text document parser."""
from pathlib import Path
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class TextParser(BaseParser):
    """Parser for plain text documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is plain text or code."""
        return file_path.suffix.lower() in {
            ".txt", ".py", ".js", ".java", ".json", ".yaml", ".yml", ".sh", ".bash"
        }

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse text file."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: unsupported extension")

        content = file_path.read_text(encoding="utf-8")

        metadata = {
            "sections": [],
            "pages": 1,
            "format": "text",
            "extension": file_path.suffix,
        }

        return ParsedDocument(
            text=content.strip(),
            metadata=metadata,
            format="text",
            source_path=file_path,
        )
