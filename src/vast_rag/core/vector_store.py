"""ChromaDB vector store for semantic search."""
import logging
from typing import Literal, Optional
import chromadb
from chromadb.config import Settings
import numpy as np
from vast_rag.types import DocumentChunk, SearchResult, CollectionName

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Manager for ChromaDB vector storage with dual collections."""

    def __init__(self, persist_directory: str = "./.chroma_db"):
        """Initialize ChromaDB with persistent storage.

        Args:
            persist_directory: Directory for ChromaDB persistence
        """
        self.persist_directory = persist_directory

        # Initialize Chroma client with persistence
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Create or get collections
        self._vast_collection = self._client.get_or_create_collection(
            name="vast_data_collection",
            metadata={"description": "VAST Data product documentation"},
        )

        self._general_collection = self._client.get_or_create_collection(
            name="general_tech_collection",
            metadata={"description": "General technical documentation"},
        )

        logger.info(f"ChromaDB initialized at {persist_directory}")
        logger.info(
            f"Collections: vast_data={self._vast_collection.count()}, "
            f"general_tech={self._general_collection.count()}"
        )

    def _get_collection(self, category: Literal["vast-data", "general-tech"]):
        """Get the appropriate collection for a category.

        Args:
            category: Document category

        Returns:
            ChromaDB collection
        """
        if category == "vast-data":
            return self._vast_collection
        else:
            return self._general_collection

    def add_documents(
        self, chunks_with_embeddings: list[tuple[DocumentChunk, np.ndarray]]
    ) -> None:
        """Add documents to appropriate collections.

        Args:
            chunks_with_embeddings: List of (chunk, embedding) tuples
        """
        # Group by category
        vast_data = []
        general_tech = []

        for chunk, embedding in chunks_with_embeddings:
            category = chunk.metadata["category"]
            if category == "vast-data":
                vast_data.append((chunk, embedding))
            else:
                general_tech.append((chunk, embedding))

        # Add to collections
        self._add_to_collection(vast_data, "vast-data")
        self._add_to_collection(general_tech, "general-tech")

        logger.info(
            f"Added {len(vast_data)} VAST Data docs, {len(general_tech)} general docs"
        )

    def _add_to_collection(
        self,
        chunks_with_embeddings: list[tuple[DocumentChunk, np.ndarray]],
        category: Literal["vast-data", "general-tech"],
    ) -> None:
        """Add chunks to a specific collection.

        Args:
            chunks_with_embeddings: List of (chunk, embedding) tuples
            category: Collection category
        """
        if not chunks_with_embeddings:
            return

        collection = self._get_collection(category)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk, embedding in chunks_with_embeddings:
            # Create unique ID from source + chunk index
            doc_id = f"{chunk.metadata['source_file']}_chunk_{chunk.chunk_index}"
            ids.append(doc_id)
            embeddings.append(embedding.tolist())
            documents.append(chunk.text)

            # Prepare metadata (must be JSON-serializable)
            metadata = {
                "source_file": chunk.metadata["source_file"],
                "category": category,
                "chunk_index": chunk.chunk_index,
            }

            # Add optional fields
            if chunk.metadata.get("page_number"):
                metadata["page_number"] = chunk.metadata["page_number"]
            if chunk.metadata.get("section"):
                metadata["section"] = chunk.metadata["section"]

            metadatas.append(metadata)

        # Upsert (add or update)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: np.ndarray,
        category: Optional[Literal["vast-data", "general-tech"]] = None,
        n_results: int = 5,
    ) -> list[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query vector
            category: Category to search, or None for both
            n_results: Number of results to return

        Returns:
            List of search results
        """
        all_results = []

        # Determine which collections to search
        if category:
            collections = [(self._get_collection(category), category)]
        else:
            collections = [
                (self._vast_collection, "vast-data"),
                (self._general_collection, "general-tech"),
            ]

        for collection, cat in collections:
            if collection.count() == 0:
                continue

            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
            )

            # Parse results
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]

                    # Convert distance to similarity score (0-1, higher is better)
                    # ChromaDB uses L2 distance by default
                    similarity = 1 / (1 + distance)

                    result = SearchResult(
                        text=results["documents"][0][i],
                        source=metadata.get("source_file", "unknown"),
                        page=metadata.get("page_number"),
                        section=metadata.get("section"),
                        score=similarity,
                        category=cat,  # type: ignore
                    )
                    all_results.append(result)

        # Sort by score and limit
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:n_results]

    def delete_by_source(
        self,
        source_file: str,
        category: Literal["vast-data", "general-tech"],
    ) -> None:
        """Delete all chunks from a source file.

        Args:
            source_file: Source filename
            category: Collection category
        """
        collection = self._get_collection(category)

        # Get all IDs for this source
        results = collection.get(where={"source_file": source_file})

        if results["ids"]:
            collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks from {source_file}")

    def get_collection_count(
        self, category: Literal["vast-data", "general-tech"]
    ) -> int:
        """Get number of documents in a collection.

        Args:
            category: Collection category

        Returns:
            Document count
        """
        collection = self._get_collection(category)
        return collection.count()

    def clear_collection(self, category: Literal["vast-data", "general-tech"]) -> None:
        """Clear all documents from a collection.

        Args:
            category: Collection category
        """
        collection = self._get_collection(category)

        # Get all IDs and delete
        all_items = collection.get()
        if all_items["ids"]:
            collection.delete(ids=all_items["ids"])
            logger.info(f"Cleared {category} collection")

    def list_collections(self) -> list[str]:
        """List all collection names.

        Returns:
            List of collection names
        """
        collections = self._client.list_collections()
        return [c.name for c in collections]

    def get_document_by_source(
        self,
        source_file: str,
        category: Literal["vast-data", "general-tech"],
    ) -> Optional[dict]:
        """Get document chunks by source file.

        Args:
            source_file: Source filename
            category: Collection category

        Returns:
            Document metadata or None
        """
        collection = self._get_collection(category)

        results = collection.get(where={"source_file": source_file}, limit=1)

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "source": results["metadatas"][0]["source_file"],
                "text": results["documents"][0],
                "metadata": results["metadatas"][0],
            }

        return None

    def reset(self) -> None:
        """Reset (delete) all collections. Use with caution!"""
        self._client.reset()
        logger.warning("All collections have been reset!")
