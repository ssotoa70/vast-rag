"""Configuration management for VAST RAG system."""
import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """Configuration for the RAG system."""

    # Paths
    docs_path: Path = Field(
        default=Path.home() / "projects" / "RAG",
        description="Directory containing documents to index"
    )
    data_path: Path = Field(
        default=Path.home() / ".claude" / "rag-data",
        description="Directory for storing ChromaDB and cache"
    )

    # Chunking
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=200)

    # Embedding
    embedding_model: str = Field(default="BAAI/bge-base-en-v1.5")
    batch_size: int = Field(default=32, ge=1, le=128)
    embedding_dimension: int = Field(default=768)

    # File watching
    debounce_seconds: float = Field(default=2.0, ge=0.5, le=10.0)

    # Caching
    query_cache_ttl: int = Field(default=300, description="Query cache TTL in seconds")
    doc_cache_size: int = Field(default=50, description="Max documents in LRU cache")

    # Allowed file extensions
    allowed_extensions: set[str] = Field(
        default={".pdf", ".md", ".html", ".docx", ".txt", ".py", ".js", ".java", ".json", ".yaml"}
    )

    @field_validator("docs_path", "data_path")
    @classmethod
    def validate_absolute_path(cls, v: Path) -> Path:
        """Ensure paths are absolute for security."""
        if not v.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return v

    class Config:
        frozen = True  # Immutable after creation


def get_config() -> Config:
    """Load configuration from environment variables."""
    env_overrides = {}

    if docs_path := os.getenv("RAG_DOCS_PATH"):
        env_overrides["docs_path"] = Path(docs_path)

    if data_path := os.getenv("RAG_DATA_PATH"):
        env_overrides["data_path"] = Path(data_path)

    if chunk_size := os.getenv("RAG_CHUNK_SIZE"):
        env_overrides["chunk_size"] = int(chunk_size)

    if chunk_overlap := os.getenv("RAG_CHUNK_OVERLAP"):
        env_overrides["chunk_overlap"] = int(chunk_overlap)

    if model := os.getenv("RAG_EMBEDDING_MODEL"):
        env_overrides["embedding_model"] = model

    if batch_size := os.getenv("RAG_BATCH_SIZE"):
        env_overrides["batch_size"] = int(batch_size)

    return Config(**env_overrides)
