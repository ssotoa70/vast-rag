"""Document indexer — orchestration layer connecting all pipeline components."""
import logging
from pathlib import Path
from typing import Literal

from vast_rag.config import Config
from vast_rag.core.chunker import SemanticChunker
from vast_rag.core.embeddings import EmbeddingService
from vast_rag.core.hash_index import FileHashIndex
from vast_rag.core.vector_store import ChromaDBManager
from vast_rag.core.watcher import FileWatcher
from vast_rag.parsers.factory import ParserFactory

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Orchestrates the document indexing pipeline.

    Pipeline: file → hash check → parse → chunk → embed → store → update hash
    """

    def __init__(self, config: Config):
        self.config = config

        # Ensure data directory exists
        config.data_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.parser_factory = ParserFactory()
        self.chunker = SemanticChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        self.hash_index = FileHashIndex(
            index_path=config.data_path / ".file_hashes.json"
        )
        self.vector_store = ChromaDBManager(
            persist_directory=str(config.data_path / "chroma_db")
        )
        self._embedding_service: EmbeddingService | None = None
        self._watcher: FileWatcher | None = None

        logger.info("DocumentIndexer initialized")

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazy-load the embedding service (model loading is expensive)."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService(
                model_name=self.config.embedding_model,
                batch_size=self.config.batch_size,
            )
        return self._embedding_service

    def categorize(self, file_path: Path) -> Literal["vast-data", "general-tech"]:
        """Categorize a document based on its path.

        Files under a directory containing 'vast' in the name are categorized
        as vast-data; everything else is general-tech.
        """
        path_str = str(file_path).lower()
        vast_keywords = ["vast", "vastdata", "vast_data", "vast-data"]
        for keyword in vast_keywords:
            if keyword in path_str:
                return "vast-data"
        return "general-tech"

    def index_file(self, file_path: Path) -> bool:
        """Index a single file through the full pipeline.

        Returns True if the file was indexed, False if skipped or failed.
        """
        # Guard: file must exist
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        # Guard: file extension must be supported
        if file_path.suffix.lower() not in self.config.allowed_extensions:
            logger.debug(f"Unsupported extension: {file_path}")
            return False

        # Guard: skip unchanged files
        if not self.hash_index.has_changed(file_path):
            logger.debug(f"Unchanged, skipping: {file_path}")
            return False

        try:
            category = self.categorize(file_path)

            # 1. Parse
            parsed = self.parser_factory.parse_document(file_path)

            # 2. Chunk
            chunks = self.chunker.chunk_document(parsed, category=category)
            if not chunks:
                logger.warning(f"No chunks produced for: {file_path}")
                return False

            # 3. Embed
            chunks_with_embeddings = self.embedding_service.embed_chunks(chunks)

            # 4. Delete old chunks for this source (idempotent re-index)
            self.vector_store.delete_by_source(file_path.name, category)

            # 5. Store new chunks
            self.vector_store.add_documents(chunks_with_embeddings)

            # 6. Update hash index
            self.hash_index.update_file(file_path)

            logger.info(
                f"Indexed {file_path.name}: {len(chunks)} chunks → {category}"
            )
            return True

        except Exception:
            logger.error(f"Failed to index {file_path}", exc_info=True)
            return False

    def index_directory(self, directory: Path | None = None) -> dict:
        """Index all supported files in a directory tree.

        Returns a stats dict with keys: total, indexed, skipped, errors.
        """
        root = directory or self.config.docs_path
        stats = {"total": 0, "indexed": 0, "skipped": 0, "errors": 0}

        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.config.allowed_extensions:
                continue

            stats["total"] += 1
            try:
                if self.index_file(file_path):
                    stats["indexed"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                stats["errors"] += 1
                logger.error(f"Error indexing {file_path}", exc_info=True)

        logger.info(
            f"Directory indexing complete: {stats['indexed']} indexed, "
            f"{stats['skipped']} skipped, {stats['errors']} errors "
            f"out of {stats['total']} files"
        )
        return stats

    def handle_file_event(
        self,
        file_path: Path,
        event_type: str,
        category: Literal["vast-data", "general-tech"],
    ) -> None:
        """Callback for the file watcher. Indexes the file.

        Args:
            file_path: Path to the changed file
            event_type: Type of event (created, modified)
            category: Document category determined by the watcher
        """
        logger.info(f"Watcher event: {event_type} {file_path} ({category})")
        self.index_file(file_path)

    def start_watching(self) -> None:
        """Start watching the docs directory for changes."""
        if self._watcher is not None:
            logger.warning("Watcher already running")
            return

        # Ensure docs directory exists
        self.config.docs_path.mkdir(parents=True, exist_ok=True)

        self._watcher = FileWatcher(
            watch_path=self.config.docs_path,
            callback=self.handle_file_event,
            debounce_seconds=self.config.debounce_seconds,
            allowed_extensions=self.config.allowed_extensions,
        )
        self._watcher.start()
        logger.info(f"Started watching {self.config.docs_path}")

    def stop_watching(self) -> None:
        """Stop watching for file changes."""
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
            logger.info("Stopped watching")

    def is_watching(self) -> bool:
        """Check if the file watcher is active."""
        return self._watcher is not None and self._watcher.is_running()
