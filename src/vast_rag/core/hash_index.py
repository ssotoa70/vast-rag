"""File hash index for tracking processed documents."""
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileHashIndex:
    """Index for tracking file hashes to detect changes."""

    def __init__(self, index_path: Path | str = "./.file_hashes.json"):
        """Initialize file hash index.

        Args:
            index_path: Path to store the hash index
        """
        self.index_path = Path(index_path)
        self._index: dict[str, str] = {}

        # Load existing index if it exists
        self._load()

        logger.info(f"File hash index initialized at {self.index_path}")

    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read file in chunks for memory efficiency
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def add_file(self, file_path: Path) -> None:
        """Add file to index with its current hash.

        Args:
            file_path: Path to file
        """
        if not file_path.exists():
            logger.warning(f"Cannot add non-existent file: {file_path}")
            return

        file_hash = self.compute_hash(file_path)
        self._index[str(file_path)] = file_hash

        logger.debug(f"Added to index: {file_path} -> {file_hash[:8]}...")

        # Auto-save on changes
        self.save()

    def update_file(self, file_path: Path) -> None:
        """Update file hash in index.

        Args:
            file_path: Path to file
        """
        self.add_file(file_path)  # Same as add (upsert behavior)

    def remove_file(self, file_path: Path) -> None:
        """Remove file from index.

        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        if file_key in self._index:
            del self._index[file_key]
            logger.debug(f"Removed from index: {file_path}")
            self.save()

    def has_file(self, file_path: Path) -> bool:
        """Check if file is in index.

        Args:
            file_path: Path to file

        Returns:
            True if file is indexed
        """
        return str(file_path) in self._index

    def get_hash(self, file_path: Path) -> Optional[str]:
        """Get stored hash for a file.

        Args:
            file_path: Path to file

        Returns:
            Hash string or None if not indexed
        """
        return self._index.get(str(file_path))

    def has_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last indexed.

        Args:
            file_path: Path to file

        Returns:
            True if file changed or not in index
        """
        if not file_path.exists():
            # File deleted - consider it changed
            return True

        if not self.has_file(file_path):
            # New file - consider it changed
            return True

        # Compare current hash with stored hash
        current_hash = self.compute_hash(file_path)
        stored_hash = self.get_hash(file_path)

        return current_hash != stored_hash

    def list_files(self) -> list[str]:
        """List all indexed files.

        Returns:
            List of file paths
        """
        return list(self._index.keys())

    def clear(self) -> None:
        """Clear all entries from index."""
        self._index.clear()
        self.save()
        logger.info("Index cleared")

    def get_stats(self) -> dict:
        """Get index statistics.

        Returns:
            Dictionary with index stats
        """
        stats = {
            "total_files": len(self._index),
            "index_path": str(self.index_path),
        }

        # Get index file size if it exists
        if self.index_path.exists():
            stats["index_size_bytes"] = self.index_path.stat().st_size
        else:
            stats["index_size_bytes"] = 0

        return stats

    def save(self) -> None:
        """Save index to disk."""
        # Create parent directory if it doesn't exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.index_path, "w") as f:
            json.dump(self._index, f, indent=2)

        logger.debug(f"Index saved to {self.index_path}")

    def _load(self) -> None:
        """Load index from disk."""
        if not self.index_path.exists():
            logger.debug("No existing index found, starting fresh")
            return

        try:
            with open(self.index_path, "r") as f:
                self._index = json.load(f)

            logger.info(f"Loaded {len(self._index)} files from index")
        except json.JSONDecodeError as e:
            logger.error(f"Error loading index: {e}. Starting fresh.")
            self._index = {}
        except Exception as e:
            logger.error(f"Unexpected error loading index: {e}. Starting fresh.")
            self._index = {}
