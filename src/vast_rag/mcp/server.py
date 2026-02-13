"""MCP server implementation for VAST RAG."""
import logging
from typing import Optional, Literal
from vast_rag.core.embeddings import EmbeddingService
from vast_rag.core.vector_store import ChromaDBManager

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP server for semantic search over VAST documentation."""

    def __init__(self):
        """Initialize MCP server with core components."""
        self.name = "vast-rag"

        # Initialize embedding service
        logger.info("Initializing embedding service...")
        self.embedding_service = EmbeddingService()

        # Initialize vector store
        logger.info("Initializing vector store...")
        self.vector_store = ChromaDBManager()

        logger.info("MCP server initialized successfully")

    def search_docs(
        self,
        query: str,
        category: Optional[Literal["vast-data", "general-tech"]] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """Search for documents using semantic similarity.

        Args:
            query: Search query text
            category: Category to search (vast-data, general-tech, or None for both)
            n_results: Number of results to return

        Returns:
            List of search results with text, source, score, and category
        """
        # Encode query to embedding
        query_embedding = self.embedding_service.encode_text(query)

        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            category=category,
            n_results=n_results,
        )

        # Convert SearchResult objects to dictionaries
        return [
            {
                "text": result.text,
                "source": result.source,
                "score": result.score,
                "category": result.category,
                "page": result.page,
                "section": result.section,
            }
            for result in results
        ]

    def list_collections(self) -> dict:
        """List all document collections with counts.

        Returns:
            Dictionary with collections list containing name and count
        """
        vast_count = self.vector_store.get_collection_count("vast-data")
        general_count = self.vector_store.get_collection_count("general-tech")

        return {
            "collections": [
                {"name": "vast-data", "count": vast_count},
                {"name": "general-tech", "count": general_count},
            ]
        }

    def get_document(
        self,
        source_file: str,
        category: Literal["vast-data", "general-tech"],
    ) -> Optional[dict]:
        """Retrieve document metadata by source file.

        Args:
            source_file: Source filename to retrieve
            category: Collection category

        Returns:
            Document metadata dict or None if not found
        """
        return self.vector_store.get_document_by_source(source_file, category)
