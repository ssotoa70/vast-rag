"""Tests for MCP server."""
import pytest
from pathlib import Path
import numpy as np
from vast_rag.types import DocumentChunk


@pytest.fixture
def mcp_server():
    """Create MCP server instance for testing."""
    from vast_rag.mcp.server import MCPServer
    return MCPServer()


@pytest.fixture
def sample_documents(mcp_server):
    """Add sample documents to vector store for testing."""
    # Create sample chunks with embeddings
    chunks = []
    embeddings = []

    for i in range(3):
        chunk = DocumentChunk(
            text=f"VAST Data is a storage system with feature {i}.",
            metadata={
                "source_file": f"vast_doc_{i}.md",
                "category": "vast-data",
                "page_number": i + 1,
            },
            chunk_index=0,
        )
        embedding = mcp_server.embedding_service.encode_text(chunk.text)
        chunks.append(chunk)
        embeddings.append(embedding)

    # Add to vector store
    mcp_server.vector_store.add_documents(list(zip(chunks, embeddings)))

    yield

    # Cleanup
    mcp_server.vector_store.clear_collection("vast-data")


def test_mcp_server_initialization(mcp_server):
    """Test that MCP server initializes with required components."""
    # Should have embedding service
    assert mcp_server.embedding_service is not None

    # Should have vector store
    assert mcp_server.vector_store is not None

    # Should have server name
    assert mcp_server.name == "vast-rag"


def test_search_docs_returns_relevant_results(mcp_server, sample_documents):
    """Test that search_docs returns relevant documents."""
    # Search for VAST Data storage
    results = mcp_server.search_docs(
        query="VAST Data storage system",
        category="vast-data",
        n_results=3
    )

    # Should return list of results
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3

    # Each result should have required fields
    for result in results:
        assert "text" in result
        assert "source" in result
        assert "score" in result
        assert "category" in result
        assert result["category"] == "vast-data"


def test_list_collections_returns_all_collections(mcp_server, sample_documents):
    """Test that list_collections returns collection information."""
    collections = mcp_server.list_collections()

    # Should return dict with collection info
    assert isinstance(collections, dict)
    assert "collections" in collections

    # Should have both collections
    collection_list = collections["collections"]
    assert isinstance(collection_list, list)
    assert len(collection_list) == 2

    # Each collection should have name and count
    for collection in collection_list:
        assert "name" in collection
        assert "count" in collection
        assert collection["name"] in ["vast-data", "general-tech"]
        assert isinstance(collection["count"], int)


def test_get_document_returns_document_metadata(mcp_server, sample_documents):
    """Test that get_document retrieves document by source file."""
    # Get document by source
    doc = mcp_server.get_document(
        source_file="vast_doc_0.md",
        category="vast-data"
    )

    # Should return document dict or None
    assert doc is not None
    assert isinstance(doc, dict)

    # Should have required fields
    assert "id" in doc
    assert "source" in doc
    assert "text" in doc
    assert doc["source"] == "vast_doc_0.md"


def test_get_document_returns_none_for_missing(mcp_server):
    """Test that get_document returns None for missing document."""
    doc = mcp_server.get_document(
        source_file="nonexistent.md",
        category="vast-data"
    )

    assert doc is None
