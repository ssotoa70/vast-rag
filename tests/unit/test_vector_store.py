"""Tests for ChromaDB vector store."""
import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil
from vast_rag.core.vector_store import ChromaDBManager
from vast_rag.types import DocumentChunk, SearchResult


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    db_path = tmp_path / "chroma_db"
    yield db_path
    # Cleanup
    if db_path.exists():
        shutil.rmtree(db_path)


@pytest.fixture
def vector_store(temp_db_path):
    """Create vector store with temporary database."""
    return ChromaDBManager(persist_directory=str(temp_db_path))


@pytest.fixture
def sample_chunks_with_embeddings():
    """Create sample chunks with embeddings."""
    chunks = []
    embeddings = []

    for i in range(3):
        metadata = {
            "source_file": f"doc{i}.txt",
            "category": "vast-data" if i % 2 == 0 else "general-tech",
            "page_number": i + 1,
            "section": f"Section {i}",
        }
        chunk = DocumentChunk(
            text=f"This is document {i} about VAST Data storage systems.",
            metadata=metadata,
            chunk_index=i,
        )
        embedding = np.random.rand(768).astype(np.float32)  # BGE-base dimension

        chunks.append(chunk)
        embeddings.append(embedding)

    return list(zip(chunks, embeddings))


def test_vector_store_initialization(vector_store):
    """Test vector store initializes with collections."""
    assert vector_store is not None

    # Check collections exist
    collections = vector_store.list_collections()
    assert "vast_data_collection" in collections
    assert "general_tech_collection" in collections


def test_vector_store_add_documents(vector_store, sample_chunks_with_embeddings):
    """Test adding documents to collections."""
    # Add documents
    vector_store.add_documents(sample_chunks_with_embeddings)

    # Check counts
    vast_count = vector_store.get_collection_count("vast-data")
    general_count = vector_store.get_collection_count("general-tech")

    assert vast_count == 2  # indices 0, 2
    assert general_count == 1  # index 1


def test_vector_store_search(vector_store, sample_chunks_with_embeddings):
    """Test semantic search returns relevant results."""
    # Add documents
    vector_store.add_documents(sample_chunks_with_embeddings)

    # Search
    query_embedding = np.random.rand(768).astype(np.float32)
    results = vector_store.search(
        query_embedding=query_embedding,
        category="vast-data",
        n_results=5,
    )

    assert isinstance(results, list)
    assert len(results) <= 5
    assert len(results) > 0  # Should have at least one result

    # Check result structure
    for result in results:
        assert isinstance(result, SearchResult)
        assert result.category == "vast-data"
        assert result.score >= 0  # Distance/similarity scores


def test_vector_store_search_both_categories(vector_store, sample_chunks_with_embeddings):
    """Test search can query both collections."""
    vector_store.add_documents(sample_chunks_with_embeddings)

    query_embedding = np.random.rand(768).astype(np.float32)
    results = vector_store.search(
        query_embedding=query_embedding,
        category=None,  # Search both
        n_results=10,
    )

    # Should get results from both collections
    categories = {r.category for r in results}
    assert len(categories) > 0  # At least one category


def test_vector_store_delete_document(vector_store, sample_chunks_with_embeddings):
    """Test deleting documents by source file."""
    # Add documents
    vector_store.add_documents(sample_chunks_with_embeddings)

    initial_count = vector_store.get_collection_count("vast-data")

    # Delete doc0.txt
    vector_store.delete_by_source("doc0.txt", category="vast-data")

    final_count = vector_store.get_collection_count("vast-data")

    assert final_count < initial_count


def test_vector_store_clear_collection(vector_store, sample_chunks_with_embeddings):
    """Test clearing entire collection."""
    # Add documents
    vector_store.add_documents(sample_chunks_with_embeddings)

    # Clear VAST Data collection
    vector_store.clear_collection("vast-data")

    count = vector_store.get_collection_count("vast-data")
    assert count == 0


def test_vector_store_get_document(vector_store, sample_chunks_with_embeddings):
    """Test retrieving document by ID."""
    # Add documents
    vector_store.add_documents(sample_chunks_with_embeddings)

    # Get first document
    doc = vector_store.get_document_by_source("doc0.txt", category="vast-data")

    assert doc is not None
    assert "doc0.txt" in doc["source"]


def test_vector_store_persistence(temp_db_path, sample_chunks_with_embeddings):
    """Test that data persists across restarts."""
    # Create store and add data
    store1 = ChromaDBManager(persist_directory=str(temp_db_path))
    store1.add_documents(sample_chunks_with_embeddings)
    count1 = store1.get_collection_count("vast-data")

    # Close and reopen
    del store1

    store2 = ChromaDBManager(persist_directory=str(temp_db_path))
    count2 = store2.get_collection_count("vast-data")

    assert count1 == count2  # Data persisted


def test_vector_store_duplicate_handling(vector_store, sample_chunks_with_embeddings):
    """Test handling of duplicate document IDs."""
    # Add same documents twice
    vector_store.add_documents(sample_chunks_with_embeddings)
    initial_count = vector_store.get_collection_count("vast-data")

    # Add again (should update, not duplicate)
    vector_store.add_documents(sample_chunks_with_embeddings)
    final_count = vector_store.get_collection_count("vast-data")

    # Count should be the same (upsert behavior)
    assert final_count == initial_count
