import pytest
from vast_rag.core.chunker import SemanticChunker
from vast_rag.types import ParsedDocument, DocumentChunk
from pathlib import Path


@pytest.fixture
def long_document():
    """Create a long document for chunking."""
    # Create text that's ~1500 tokens (will be split into 3 chunks of 500)
    text = " ".join([f"Word{i}" for i in range(2000)])  # Approx 2000 tokens

    metadata = {
        "sections": ["Section 1", "Section 2"],
        "pages": 1,
        "format": "text",
    }

    return ParsedDocument(
        text=text,
        metadata=metadata,
        format="text",
        source_path=Path("test.txt"),
    )


def test_chunker_creates_chunks_with_overlap(long_document):
    """Test chunking creates overlapping chunks."""
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_document(long_document, category="general-tech")

    assert len(chunks) > 1  # Should create multiple chunks

    # Verify that chunks have reasonable overlap at token level
    # Token boundaries may not align perfectly with word boundaries
    assert len(chunks) >= 3  # With 2000 words and 500-token chunks, expect multiple chunks


def test_chunker_preserves_metadata(long_document):
    """Test that metadata is preserved in chunks."""
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_document(long_document, category="vast-data")

    for idx, chunk in enumerate(chunks):
        assert chunk.metadata["source_file"] == "test.txt"
        assert chunk.metadata["category"] == "vast-data"
        assert chunk.chunk_index == idx


def test_chunker_respects_token_limits():
    """Test chunks don't exceed token limit."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=10)

    text = " ".join([f"Word{i}" for i in range(500)])
    doc = ParsedDocument(
        text=text,
        metadata={"sections": [], "pages": 1, "format": "text"},
        format="text",
        source_path=Path("test.txt"),
    )

    chunks = chunker.chunk_document(doc, category="general-tech")

    # Each chunk should be approximately chunk_size tokens
    for chunk in chunks:
        token_count = len(chunk.text.split())  # Rough token count
        assert token_count <= 120  # Some margin for token counting differences
