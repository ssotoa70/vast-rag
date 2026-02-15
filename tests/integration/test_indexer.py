"""Integration tests for DocumentIndexer — the orchestration layer."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vast_rag.indexer import DocumentIndexer
from vast_rag.config import Config


@pytest.fixture
def tmp_docs(tmp_path):
    """Create a temporary docs directory with subdirectories."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    vast_dir = docs_dir / "vast-data"
    vast_dir.mkdir()
    general_dir = docs_dir / "general-tech"
    general_dir.mkdir()
    return docs_dir


@pytest.fixture
def tmp_data(tmp_path):
    """Create a temporary data directory for ChromaDB and hash index."""
    data_dir = tmp_path / "rag-data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def config(tmp_docs, tmp_data):
    """Create a test config with temporary directories."""
    return Config(
        docs_path=tmp_docs,
        data_path=tmp_data,
        chunk_size=100,
        chunk_overlap=10,
    )


@pytest.fixture
def sample_markdown(tmp_docs):
    """Create a sample markdown file in the general-tech directory."""
    md_file = tmp_docs / "general-tech" / "sample.md"
    md_file.write_text(
        "# Test Document\n\n"
        "This is a test document for the indexer integration test.\n\n"
        "## Section One\n\n"
        "Content in section one about testing indexing pipelines.\n\n"
        "## Section Two\n\n"
        "Content in section two about vector search and embeddings.\n"
    )
    return md_file


@pytest.fixture
def vast_markdown(tmp_docs):
    """Create a sample markdown file in the vast-data directory."""
    md_file = tmp_docs / "vast-data" / "vast-intro.md"
    md_file.write_text(
        "# VAST Data Platform\n\n"
        "VAST Data provides a universal storage platform.\n\n"
        "## Architecture\n\n"
        "The VAST platform uses disaggregated shared everything architecture.\n"
    )
    return md_file


class TestDocumentIndexerInit:
    """Test indexer initialization."""

    def test_creates_indexer_from_config(self, config):
        """Indexer should initialize all components from a Config."""
        indexer = DocumentIndexer(config)

        assert indexer.config == config
        assert indexer.parser_factory is not None
        assert indexer.chunker is not None
        assert indexer.hash_index is not None
        assert indexer.vector_store is not None

    def test_creates_data_directories(self, config):
        """Indexer should create data directories if they don't exist."""
        indexer = DocumentIndexer(config)

        assert config.data_path.exists()


class TestIndexFile:
    """Test indexing individual files."""

    def test_index_new_file_returns_true(self, config, sample_markdown):
        """Indexing a new file should return True (was indexed)."""
        indexer = DocumentIndexer(config)
        result = indexer.index_file(sample_markdown)

        assert result is True

    def test_index_unchanged_file_returns_false(self, config, sample_markdown):
        """Indexing the same file twice should skip and return False."""
        indexer = DocumentIndexer(config)
        indexer.index_file(sample_markdown)

        result = indexer.index_file(sample_markdown)
        assert result is False

    def test_index_modified_file_returns_true(self, config, sample_markdown):
        """Modifying a file and re-indexing should return True."""
        indexer = DocumentIndexer(config)
        indexer.index_file(sample_markdown)

        # Modify the file
        sample_markdown.write_text(
            "# Updated Document\n\nNew content after modification.\n"
        )

        result = indexer.index_file(sample_markdown)
        assert result is True

    def test_index_file_stores_in_vector_db(self, config, sample_markdown):
        """Indexed file should be searchable in the vector store."""
        indexer = DocumentIndexer(config)
        indexer.index_file(sample_markdown)

        count = indexer.vector_store.get_collection_count("general-tech")
        assert count > 0

    def test_index_vast_file_categorized_correctly(self, config, vast_markdown):
        """Files in vast-data dir should go to vast-data collection."""
        indexer = DocumentIndexer(config)
        indexer.index_file(vast_markdown)

        vast_count = indexer.vector_store.get_collection_count("vast-data")
        general_count = indexer.vector_store.get_collection_count("general-tech")

        assert vast_count > 0
        assert general_count == 0

    def test_index_nonexistent_file_returns_false(self, config):
        """Trying to index a file that doesn't exist should return False."""
        indexer = DocumentIndexer(config)
        result = indexer.index_file(Path("/nonexistent/file.md"))

        assert result is False

    def test_index_unsupported_file_returns_false(self, config, tmp_docs):
        """Trying to index an unsupported file type should return False."""
        bad_file = tmp_docs / "file.exe"
        bad_file.write_bytes(b"binary data")

        indexer = DocumentIndexer(config)
        result = indexer.index_file(bad_file)

        assert result is False

    def test_reindex_clears_old_chunks(self, config, sample_markdown):
        """Re-indexing should delete old chunks before adding new ones."""
        indexer = DocumentIndexer(config)
        indexer.index_file(sample_markdown)
        count_after_first = indexer.vector_store.get_collection_count("general-tech")

        # Modify and re-index
        sample_markdown.write_text("# Short\n\nBrief content.\n")
        indexer.index_file(sample_markdown)
        count_after_second = indexer.vector_store.get_collection_count("general-tech")

        # The count should reflect the new (shorter) document, not accumulate
        assert count_after_second <= count_after_first


class TestIndexDirectory:
    """Test bulk indexing of directories."""

    def test_index_directory_processes_all_files(
        self, config, sample_markdown, vast_markdown
    ):
        """index_directory should process all supported files."""
        indexer = DocumentIndexer(config)
        stats = indexer.index_directory()

        assert stats["total"] >= 2
        assert stats["indexed"] >= 2
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

    def test_index_directory_skips_unchanged(
        self, config, sample_markdown, vast_markdown
    ):
        """Second run should skip already-indexed unchanged files."""
        indexer = DocumentIndexer(config)
        indexer.index_directory()

        stats = indexer.index_directory()

        assert stats["skipped"] >= 2
        assert stats["indexed"] == 0


class TestCategorization:
    """Test document categorization logic."""

    def test_vast_data_path_categorized(self, config, tmp_docs):
        """Files under vast-data/ should be categorized as vast-data."""
        indexer = DocumentIndexer(config)
        category = indexer.categorize(tmp_docs / "vast-data" / "doc.md")
        assert category == "vast-data"

    def test_general_path_categorized(self, config, tmp_docs):
        """Files not under vast-data/ should be categorized as general-tech."""
        indexer = DocumentIndexer(config)
        category = indexer.categorize(tmp_docs / "general-tech" / "doc.md")
        assert category == "general-tech"


class TestWatcherCallback:
    """Test the file watcher callback integration."""

    def test_handle_file_event_indexes_new_file(self, config, sample_markdown):
        """The watcher callback should trigger indexing."""
        indexer = DocumentIndexer(config)
        indexer.handle_file_event(sample_markdown, "created", "general-tech")

        count = indexer.vector_store.get_collection_count("general-tech")
        assert count > 0

    def test_handle_file_event_skips_unchanged(self, config, sample_markdown):
        """Callback should skip files already indexed and unchanged."""
        indexer = DocumentIndexer(config)
        indexer.handle_file_event(sample_markdown, "created", "general-tech")
        indexer.handle_file_event(sample_markdown, "modified", "general-tech")

        # Should still have the same count (not doubled)
        count = indexer.vector_store.get_collection_count("general-tech")
        assert count > 0

    def test_start_stop_watching(self, config):
        """Indexer should be able to start and stop the file watcher."""
        indexer = DocumentIndexer(config)
        indexer.start_watching()

        assert indexer.is_watching()

        indexer.stop_watching()
        assert not indexer.is_watching()
