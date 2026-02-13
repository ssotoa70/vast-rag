"""Semantic chunking for documents."""
import logging
from typing import Literal
import tiktoken
from vast_rag.types import ParsedDocument, DocumentChunk

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Chunks documents semantically with overlap."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize chunker.

        Args:
            chunk_size: Target tokens per chunk
            chunk_overlap: Overlap tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk_document(
        self,
        document: ParsedDocument,
        category: Literal["vast-data", "general-tech"],
    ) -> list[DocumentChunk]:
        """Chunk a document into smaller pieces.

        Args:
            document: Parsed document to chunk
            category: Document category for metadata

        Returns:
            List of document chunks with metadata
        """
        # For PDFs, chunk by page first if available
        if document.format == "pdf" and "page_texts" in document.metadata:
            return self._chunk_pdf(document, category)

        # For other formats, chunk the full text
        return self._chunk_text(
            text=document.text,
            source_file=document.source_path.name,
            category=category,
            sections=document.sections,
        )

    def _chunk_pdf(
        self,
        document: ParsedDocument,
        category: Literal["vast-data", "general-tech"],
    ) -> list[DocumentChunk]:
        """Chunk PDF by pages to preserve page numbers."""
        chunks = []
        chunk_index = 0

        page_texts = document.metadata["page_texts"]

        for page_num, page_text in enumerate(page_texts, start=1):
            # Chunk each page
            page_chunks = self._chunk_text(
                text=page_text,
                source_file=document.source_path.name,
                category=category,
                sections=document.sections,
                page_number=page_num,
            )

            # Update chunk indices
            for chunk in page_chunks:
                chunk.chunk_index = chunk_index
                chunk_index += 1

            chunks.extend(page_chunks)

        return chunks

    def _chunk_text(
        self,
        text: str,
        source_file: str,
        category: Literal["vast-data", "general-tech"],
        sections: list[str],
        page_number: int | None = None,
    ) -> list[DocumentChunk]:
        """Chunk text with overlap.

        Args:
            text: Text to chunk
            source_file: Source filename
            category: Document category
            sections: Section headers from document
            page_number: Optional page number

        Returns:
            List of chunks
        """
        # Tokenize
        tokens = self._tokenizer.encode(text)

        if len(tokens) <= self.chunk_size:
            # Document fits in one chunk
            metadata = {
                "source_file": source_file,
                "category": category,
                "page_number": page_number,
                "section": sections[0] if sections else None,
            }
            return [
                DocumentChunk(
                    text=text,
                    metadata=metadata,
                    chunk_index=0,
                )
            ]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(tokens):
            # Get chunk with overlap
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]

            # Decode back to text
            chunk_text = self._tokenizer.decode(chunk_tokens)

            metadata = {
                "source_file": source_file,
                "category": category,
                "page_number": page_number,
                "section": self._find_section(chunk_text, sections),
            }

            chunks.append(
                DocumentChunk(
                    text=chunk_text.strip(),
                    metadata=metadata,
                    chunk_index=chunk_index,
                )
            )

            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            chunk_index += 1

        return chunks

    def _find_section(self, text: str, sections: list[str]) -> str | None:
        """Find which section this text belongs to."""
        for section in sections:
            if section in text:
                return section
        return None
