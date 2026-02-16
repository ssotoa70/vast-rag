"""Tests for the production MCP server entry point."""
import json
import pytest
from pathlib import Path

from vast_rag.config import Config
from vast_rag.server import create_server, _handle_list_collections, _handle_get_document


@pytest.fixture
def server_pair(tmp_path):
    """Create a server + indexer pair with temp directories."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "vast-data").mkdir()
    (docs / "general-tech").mkdir()
    data = tmp_path / "rag-data"
    data.mkdir()

    config = Config(
        docs_path=docs,
        data_path=data,
        chunk_size=200,
        chunk_overlap=20,
    )
    app, indexer = create_server(config)
    return app, indexer


class TestServerCreation:
    """Test MCP server and indexer are wired correctly."""

    def test_creates_server_with_name(self, server_pair):
        app, _ = server_pair
        assert app.name == "vast-rag"

    def test_creates_indexer(self, server_pair):
        _, indexer = server_pair
        assert indexer is not None
        assert indexer.vector_store is not None


class TestToolHandlers:
    """Test the synchronous tool handler functions."""

    def test_list_collections_returns_json(self, server_pair):
        _, indexer = server_pair
        result = _handle_list_collections(indexer)

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "collections" in data
        assert "total_chunks" in data
        names = [c["name"] for c in data["collections"]]
        assert "vast-data" in names
        assert "general-tech" in names

    def test_get_document_not_found(self, server_pair):
        _, indexer = server_pair
        result = _handle_get_document(indexer, {
            "source_file": "nonexistent.md",
            "category": "vast-data",
        })

        assert "not found" in result[0].text.lower()
