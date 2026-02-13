"""Type definitions for VAST RAG system."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class ParsedDocument:
    """Represents a parsed document with extracted text and metadata."""

    text: str
    metadata: dict
    format: str
    source_path: Path

    @property
    def pages(self) -> int:
        """Number of pages in the document."""
        return self.metadata.get("pages", 1)

    @property
    def sections(self) -> list[str]:
        """Section headers found in the document."""
        return self.metadata.get("sections", [])


@dataclass
class DocumentChunk:
    """A chunk of text from a document with metadata."""

    text: str
    metadata: dict
    chunk_index: int

    @property
    def source_file(self) -> str:
        """Original source file name."""
        return self.metadata["source_file"]

    @property
    def page_number(self) -> int | None:
        """Page number this chunk came from."""
        return self.metadata.get("page_number")

    @property
    def section(self) -> str | None:
        """Section header this chunk belongs to."""
        return self.metadata.get("section")


@dataclass
class SearchResult:
    """A search result with text, metadata, and similarity score."""

    text: str
    source: str
    page: int | None
    section: str | None
    score: float
    category: Literal["vast-data", "general-tech"]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "source": self.source,
            "page": self.page,
            "section": self.section,
            "score": round(self.score, 3),
            "category": self.category,
        }


CollectionName = Literal["vast_data_collection", "general_tech_collection"]
