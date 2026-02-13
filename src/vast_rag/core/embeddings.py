"""Embedding service for converting text to vectors."""
import logging
from functools import lru_cache
from typing import Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from vast_rag.types import DocumentChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings from text."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        batch_size: int = 32,
        cache_size: int = 1000,
    ):
        """Initialize embedding service.

        Args:
            model_name: Name of the sentence-transformers model
            batch_size: Number of texts to encode in a batch
            cache_size: Maximum number of embeddings to cache
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_size = cache_size

        logger.info(f"Loading embedding model: {model_name}")
        self._model = SentenceTransformer(model_name)
        self._cache: dict[str, np.ndarray] = {}

        # Get embedding dimension from model
        self.embedding_dim = self._model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def encode_text(self, text: str) -> np.ndarray:
        """Encode a single text into an embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector as numpy array
        """
        # Check cache first
        if text in self._cache:
            return self._cache[text]

        # Encode text
        embedding = self._model.encode(text, convert_to_numpy=True)

        # Cache the result
        self._add_to_cache(text, embedding)

        return embedding

    def encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Encode multiple texts in batches.

        Args:
            texts: List of texts to encode

        Returns:
            List of embedding vectors
        """
        # Check cache for each text
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        for idx, text in enumerate(texts):
            if text in self._cache:
                embeddings.append(self._cache[text])
            else:
                uncached_texts.append(text)
                uncached_indices.append(idx)
                embeddings.append(None)  # Placeholder

        # Encode uncached texts
        if uncached_texts:
            logger.debug(f"Encoding {len(uncached_texts)} uncached texts")
            new_embeddings = self._model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                show_progress_bar=len(uncached_texts) > 100,
            )

            # Fill in the placeholders and cache results
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
                embeddings[idx] = emb
                self._add_to_cache(text, emb)

        return embeddings

    def embed_chunks(
        self, chunks: list[DocumentChunk]
    ) -> list[tuple[DocumentChunk, np.ndarray]]:
        """Embed a list of document chunks.

        Args:
            chunks: List of document chunks to embed

        Returns:
            List of (chunk, embedding) tuples
        """
        texts = [chunk.text for chunk in chunks]
        embeddings = self.encode_batch(texts)

        return list(zip(chunks, embeddings))

    def _add_to_cache(self, text: str, embedding: np.ndarray) -> None:
        """Add embedding to cache with LRU eviction.

        Args:
            text: Text key
            embedding: Embedding to cache
        """
        # Simple LRU: if cache is full, remove oldest entry
        if len(self._cache) >= self.cache_size:
            # Remove first item (oldest in insertion order for Python 3.7+)
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[text] = embedding

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.debug("Embedding cache cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and hit rate
        """
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.cache_size,
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
        }
