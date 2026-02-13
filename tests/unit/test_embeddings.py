"""Tests for embedding service."""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from vast_rag.core.embeddings import EmbeddingService
from vast_rag.types import DocumentChunk
from pathlib import Path


@pytest.fixture
def mock_model():
    """Create a mock sentence transformer model."""
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = 384
    model.encode.side_effect = lambda text, **kwargs: (
        np.random.rand(384) if isinstance(text, str)
        else np.random.rand(len(text), 384)
    )
    return model


@pytest.fixture
def embedding_service(mock_model):
    """Create embedding service with mocked model."""
    with patch('vast_rag.core.embeddings.SentenceTransformer', return_value=mock_model):
        service = EmbeddingService(model_name="test-model", batch_size=4)
        return service


@pytest.fixture
def sample_chunks():
    """Create sample document chunks for testing."""
    chunks = []
    for i in range(5):
        metadata = {
            "source_file": f"doc{i}.txt",
            "category": "general-tech",
            "page_number": None,
            "section": None,
        }
        chunks.append(
            DocumentChunk(
                text=f"This is test document number {i} with some content.",
                metadata=metadata,
                chunk_index=i,
            )
        )
    return chunks


def test_embedding_service_initialization(embedding_service):
    """Test embedding service initializes correctly."""
    assert embedding_service is not None
    assert embedding_service.batch_size == 4
    assert embedding_service.embedding_dim > 0


def test_embedding_service_encodes_text(embedding_service):
    """Test encoding single text produces correct shape."""
    text = "This is a test document about machine learning."
    embedding = embedding_service.encode_text(text)

    assert isinstance(embedding, np.ndarray)
    assert len(embedding.shape) == 1  # 1D vector
    assert embedding.shape[0] == embedding_service.embedding_dim


def test_embedding_service_batch_encode(embedding_service, sample_chunks):
    """Test batch encoding produces correct number of embeddings."""
    texts = [chunk.text for chunk in sample_chunks]
    embeddings = embedding_service.encode_batch(texts)

    assert isinstance(embeddings, list)
    assert len(embeddings) == len(texts)

    for emb in embeddings:
        assert isinstance(emb, np.ndarray)
        assert emb.shape[0] == embedding_service.embedding_dim


def test_embedding_service_semantic_similarity(embedding_service):
    """Test that similar texts have higher similarity."""
    text1 = "Python is a programming language."
    text2 = "Python is used for coding."
    text3 = "The weather is nice today."

    emb1 = embedding_service.encode_text(text1)
    emb2 = embedding_service.encode_text(text2)
    emb3 = embedding_service.encode_text(text3)

    # Cosine similarity between similar texts should be higher
    sim_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    sim_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))

    assert sim_12 > sim_13  # Similar texts should have higher similarity


def test_embedding_service_caching(embedding_service):
    """Test that embeddings are cached for repeated texts."""
    text = "This text should be cached."

    # First encode
    emb1 = embedding_service.encode_text(text)

    # Second encode (should use cache)
    emb2 = embedding_service.encode_text(text)

    # Should be identical (same object if cached)
    assert np.array_equal(emb1, emb2)

    # Cache should contain the text
    assert len(embedding_service._cache) > 0


def test_embedding_service_cache_limit(embedding_service):
    """Test that cache respects maximum size."""
    embedding_service._cache.clear()
    embedding_service.cache_size = 3  # Small cache for testing

    # Add more items than cache size
    for i in range(5):
        embedding_service.encode_text(f"Text number {i}")

    # Cache should not exceed limit
    assert len(embedding_service._cache) <= 3


def test_embedding_service_embed_chunks(embedding_service, sample_chunks):
    """Test embedding full chunks with metadata."""
    results = embedding_service.embed_chunks(sample_chunks)

    assert len(results) == len(sample_chunks)

    for chunk, embedding in results:
        assert isinstance(chunk, DocumentChunk)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == embedding_service.embedding_dim
