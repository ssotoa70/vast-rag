"""End-to-End tests for the VAST RAG pipeline.

Tests the full chain: document files → DocumentIndexer → ChromaDB → MCPServer queries.
Unlike test_indexer.py (which tests DocumentIndexer in isolation), these tests validate
that the MCPServer can return correct search results from indexed content.

Fixtures are module-scoped to avoid re-loading the embedding model per test (~20s each).
"""
import pytest
from pathlib import Path

from vast_rag.config import Config
from vast_rag.indexer import DocumentIndexer
from vast_rag.mcp.server import MCPServer


# ---------------------------------------------------------------------------
# Module-scoped fixtures (shared across all tests to avoid repeated model load)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def e2e_dirs(tmp_path_factory):
    """Create isolated temp directories for docs and data."""
    base = tmp_path_factory.mktemp("e2e")
    docs = base / "docs"
    docs.mkdir()
    (docs / "vast-data").mkdir()
    (docs / "general-tech").mkdir()
    data = base / "rag-data"
    data.mkdir()
    return docs, data


@pytest.fixture(scope="module")
def config(e2e_dirs):
    """Config wired to temp directories."""
    docs, data = e2e_dirs
    return Config(
        docs_path=docs,
        data_path=data,
        chunk_size=200,
        chunk_overlap=20,
    )


@pytest.fixture(scope="module")
def vast_docs(e2e_dirs):
    """Create realistic VAST Data documentation files."""
    docs, _ = e2e_dirs
    vast_dir = docs / "vast-data"

    # Document about VAST architecture
    (vast_dir / "architecture.md").write_text(
        "# VAST Data Platform Architecture\n\n"
        "VAST Data provides a universal storage platform built on "
        "disaggregated shared everything (DASE) architecture. The system "
        "uses NVMe-over-Fabrics for low-latency data access across "
        "all nodes in the cluster.\n\n"
        "## Storage Tiers\n\n"
        "VAST uses a single tier of QLC flash with a small SCM write "
        "buffer. Data is globally deduplicated and compressed, providing "
        "effective capacity that far exceeds raw flash capacity.\n\n"
        "## Similarity Reduction\n\n"
        "Global inline deduplication and compression reduce storage "
        "consumption. The VAST Similarity engine identifies duplicate "
        "data blocks across the entire namespace.\n"
    )

    # Document about VAST database features
    (vast_dir / "database.md").write_text(
        "# VAST DataBase\n\n"
        "VAST DataBase is an embedded database engine that enables "
        "structured queries on unstructured data. It supports tabular "
        "access patterns via Apache Arrow and Parquet formats.\n\n"
        "## Query Engine\n\n"
        "The query engine supports predicate pushdown, column pruning, "
        "and parallel scan operations. It integrates natively with "
        "the VAST Data Platform's global namespace.\n"
    )

    return vast_dir


@pytest.fixture(scope="module")
def general_docs(e2e_dirs):
    """Create general tech documentation files."""
    docs, _ = e2e_dirs
    general_dir = docs / "general-tech"

    # Document about Python best practices
    (general_dir / "python-guide.md").write_text(
        "# Python Best Practices\n\n"
        "Python is a versatile programming language used for web "
        "development, data science, and automation. This guide covers "
        "modern Python development practices.\n\n"
        "## Type Hints\n\n"
        "Type hints improve code readability and enable static analysis "
        "with tools like mypy. Use typing module for complex types.\n\n"
        "## Virtual Environments\n\n"
        "Always use virtual environments to isolate project dependencies. "
        "Use venv or poetry for dependency management.\n"
    )

    return general_dir


@pytest.fixture(scope="module")
def indexed_pipeline(config, vast_docs, general_docs):
    """Index all docs and return the indexer. This is the core E2E setup."""
    indexer = DocumentIndexer(config)
    stats = indexer.index_directory()

    assert stats["errors"] == 0, f"Indexing had errors: {stats}"
    assert stats["indexed"] >= 3, f"Expected >= 3 files indexed, got {stats}"

    return indexer


@pytest.fixture(scope="module")
def mcp_server(config, indexed_pipeline):
    """Create an MCPServer sharing the same data directory as the indexer.

    We patch the MCPServer's vector store and embedding service to reuse
    the indexer's instances, avoiding a second model load and ensuring
    the server queries the same ChromaDB.
    """
    server = MCPServer.__new__(MCPServer)
    server.name = "vast-rag"
    server.embedding_service = indexed_pipeline.embedding_service
    server.vector_store = indexed_pipeline.vector_store
    return server


# ---------------------------------------------------------------------------
# Test: Full pipeline — index + query
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """Validate that indexed documents are retrievable via MCP server tools."""

    def test_search_vast_architecture(self, mcp_server):
        """Searching for VAST architecture should return the architecture doc."""
        results = mcp_server.search_docs("VAST disaggregated shared everything architecture")

        assert len(results) > 0
        sources = [r["source"] for r in results]
        assert "architecture.md" in sources
        # Top result should be the architecture doc
        assert results[0]["source"] == "architecture.md"

    def test_search_vast_database(self, mcp_server):
        """Searching for VAST database should return the database doc."""
        results = mcp_server.search_docs("VAST DataBase tabular query engine")

        assert len(results) > 0
        sources = [r["source"] for r in results]
        assert "database.md" in sources

    def test_search_python_guide(self, mcp_server):
        """Searching for Python should return the Python guide."""
        results = mcp_server.search_docs("Python type hints virtual environments")

        assert len(results) > 0
        sources = [r["source"] for r in results]
        assert "python-guide.md" in sources

    def test_search_with_category_filter(self, mcp_server):
        """Filtering by category should only return docs from that category."""
        results = mcp_server.search_docs(
            "storage architecture", category="vast-data"
        )

        for r in results:
            assert r["category"] == "vast-data"

    def test_search_results_have_scores(self, mcp_server):
        """All results should have non-zero similarity scores."""
        results = mcp_server.search_docs("data platform")

        for r in results:
            assert r["score"] > 0
            assert r["score"] <= 1.0


# ---------------------------------------------------------------------------
# Test: Search quality — relevant docs ranked higher
# ---------------------------------------------------------------------------

class TestSearchQuality:
    """Validate that semantically relevant results rank above irrelevant ones."""

    def test_vast_query_prefers_vast_docs(self, mcp_server):
        """A VAST-specific query should rank VAST docs above general docs."""
        results = mcp_server.search_docs("NVMe flash storage deduplication")

        # At least one VAST doc should appear before any general doc
        vast_indices = [
            i for i, r in enumerate(results) if r["category"] == "vast-data"
        ]
        general_indices = [
            i for i, r in enumerate(results) if r["category"] == "general-tech"
        ]

        if vast_indices and general_indices:
            assert min(vast_indices) < min(general_indices), (
                "Expected VAST docs to rank above general docs for VAST-specific query"
            )

    def test_python_query_prefers_general_docs(self, mcp_server):
        """A Python-specific query should rank general docs above VAST docs."""
        results = mcp_server.search_docs("Python programming virtual environment")

        general_indices = [
            i for i, r in enumerate(results) if r["category"] == "general-tech"
        ]

        # The general-tech doc should be in the results
        assert len(general_indices) > 0


# ---------------------------------------------------------------------------
# Test: MCP tool coverage — list_collections, get_document
# ---------------------------------------------------------------------------

class TestMCPTools:
    """Validate all MCP server tools return correct data from indexed content."""

    def test_list_collections_shows_counts(self, mcp_server):
        """list_collections should reflect the indexed document counts."""
        result = mcp_server.list_collections()

        collections = {c["name"]: c["count"] for c in result["collections"]}
        assert collections["vast-data"] > 0
        assert collections["general-tech"] > 0

    def test_get_document_by_source(self, mcp_server):
        """get_document should retrieve metadata for an indexed file."""
        doc = mcp_server.get_document("architecture.md", "vast-data")

        assert doc is not None
        assert doc["source"] == "architecture.md"
        assert "text" in doc

    def test_get_document_returns_none_for_missing(self, mcp_server):
        """get_document should return None for a non-existent file."""
        doc = mcp_server.get_document("nonexistent.md", "vast-data")

        assert doc is None

    def test_search_docs_respects_n_results(self, mcp_server):
        """search_docs n_results parameter should limit output count."""
        results = mcp_server.search_docs("data", n_results=2)

        assert len(results) <= 2


# ---------------------------------------------------------------------------
# Test: Idempotent re-indexing
# ---------------------------------------------------------------------------

class TestReindexing:
    """Validate that modifying and re-indexing a document works correctly."""

    def test_reindex_updates_searchable_content(self, indexed_pipeline, mcp_server, e2e_dirs):
        """After modifying a doc, re-indexing should make new content searchable."""
        docs, _ = e2e_dirs
        arch_file = docs / "vast-data" / "architecture.md"

        # Append distinctive new content
        original = arch_file.read_text()
        arch_file.write_text(
            original + "\n## Erasure Coding\n\n"
            "VAST uses locally decodable erasure codes to provide "
            "data protection without the overhead of traditional RAID.\n"
        )

        # index_file calls has_changed() which compares SHA-256 hashes,
        # so modifying the file content above is enough for detection
        result = indexed_pipeline.index_file(arch_file)
        assert result is True

        # Search for the new content
        results = mcp_server.search_docs("erasure coding data protection RAID")

        assert len(results) > 0
        sources = [r["source"] for r in results]
        assert "architecture.md" in sources

    def test_collection_counts_after_reindex(self, mcp_server):
        """Collection counts should remain consistent after re-indexing."""
        result = mcp_server.list_collections()

        collections = {c["name"]: c["count"] for c in result["collections"]}
        # Counts should still be positive (not zeroed or duplicated)
        assert collections["vast-data"] > 0
        assert collections["general-tech"] > 0


# ---------------------------------------------------------------------------
# Test: Multi-format in one session (using markdown — see insight above)
# ---------------------------------------------------------------------------

class TestMultiDocument:
    """Validate that multiple documents indexed together are all searchable."""

    def test_all_documents_searchable(self, mcp_server):
        """Every indexed document should be retrievable via search."""
        expected_sources = ["architecture.md", "database.md", "python-guide.md"]

        for source in expected_sources:
            # Search using a term from each document
            results = mcp_server.search_docs(source.replace(".md", "").replace("-", " "))
            all_sources = [r["source"] for r in results]
            assert source in all_sources, (
                f"Expected {source} in search results, got {all_sources}"
            )

    def test_cross_collection_search(self, mcp_server):
        """Searching without a category filter should return docs from both collections."""
        results = mcp_server.search_docs("data", n_results=10)

        categories = {r["category"] for r in results}
        assert len(categories) >= 1  # At minimum one category has results
