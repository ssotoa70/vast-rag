import os
from pathlib import Path
import pytest
from vast_rag.config import Config, get_config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.chunk_size == 500
    assert config.chunk_overlap == 50
    assert config.embedding_model == "BAAI/bge-base-en-v1.5"
    assert config.batch_size == 32


def test_config_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("RAG_DOCS_PATH", "/custom/docs")
    monkeypatch.setenv("RAG_CHUNK_SIZE", "1000")

    config = get_config()
    assert str(config.docs_path) == "/custom/docs"
    assert config.chunk_size == 1000


def test_config_path_validation():
    """Test that docs_path must be absolute."""
    with pytest.raises(ValueError, match="must be absolute"):
        Config(docs_path=Path("relative/path"))
