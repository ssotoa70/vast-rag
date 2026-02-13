"""Tests for file hash index."""
import pytest
import json
from pathlib import Path
from vast_rag.core.hash_index import FileHashIndex


@pytest.fixture
def temp_index_file(tmp_path):
    """Create temporary index file path."""
    return tmp_path / "hash_index.json"


@pytest.fixture
def hash_index(temp_index_file):
    """Create hash index with temporary storage."""
    return FileHashIndex(index_path=temp_index_file)


@pytest.fixture
def sample_files(tmp_path):
    """Create sample files for testing."""
    files_dir = tmp_path / "docs"
    files_dir.mkdir()

    file1 = files_dir / "doc1.txt"
    file1.write_text("This is document 1 content.")

    file2 = files_dir / "doc2.md"
    file2.write_text("# Document 2\n\nSome markdown content.")

    file3 = files_dir / "doc3.pdf"
    file3.write_bytes(b"PDF binary content")

    return [file1, file2, file3]


def test_hash_index_initialization(temp_index_file):
    """Test hash index initializes correctly."""
    index = FileHashIndex(index_path=temp_index_file)
    assert index is not None
    assert index.index_path == temp_index_file


def test_hash_index_computes_file_hash(hash_index, sample_files):
    """Test computing file hash."""
    file_path = sample_files[0]
    file_hash = hash_index.compute_hash(file_path)

    assert file_hash is not None
    assert len(file_hash) == 64  # SHA-256 produces 64 hex characters
    assert isinstance(file_hash, str)


def test_hash_index_same_content_same_hash(hash_index, tmp_path):
    """Test that identical content produces identical hash."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"

    content = "Identical content"
    file1.write_text(content)
    file2.write_text(content)

    hash1 = hash_index.compute_hash(file1)
    hash2 = hash_index.compute_hash(file2)

    assert hash1 == hash2


def test_hash_index_different_content_different_hash(hash_index, tmp_path):
    """Test that different content produces different hash."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"

    file1.write_text("Content A")
    file2.write_text("Content B")

    hash1 = hash_index.compute_hash(file1)
    hash2 = hash_index.compute_hash(file2)

    assert hash1 != hash2


def test_hash_index_add_file(hash_index, sample_files):
    """Test adding file to index."""
    file_path = sample_files[0]

    hash_index.add_file(file_path)

    # Check if file is in index
    assert hash_index.has_file(file_path)


def test_hash_index_get_hash(hash_index, sample_files):
    """Test retrieving file hash from index."""
    file_path = sample_files[0]

    hash_index.add_file(file_path)
    stored_hash = hash_index.get_hash(file_path)

    # Compute expected hash
    expected_hash = hash_index.compute_hash(file_path)

    assert stored_hash == expected_hash


def test_hash_index_detect_changed_file(hash_index, tmp_path):
    """Test detecting when file content changes."""
    file_path = tmp_path / "doc.txt"
    file_path.write_text("Original content")

    # Add to index
    hash_index.add_file(file_path)
    assert not hash_index.has_changed(file_path)

    # Modify file
    file_path.write_text("Modified content")

    # Should detect change
    assert hash_index.has_changed(file_path)


def test_hash_index_detect_unchanged_file(hash_index, tmp_path):
    """Test detecting unchanged files."""
    file_path = tmp_path / "doc.txt"
    file_path.write_text("Content")

    hash_index.add_file(file_path)

    # File hasn't changed
    assert not hash_index.has_changed(file_path)


def test_hash_index_remove_file(hash_index, sample_files):
    """Test removing file from index."""
    file_path = sample_files[0]

    hash_index.add_file(file_path)
    assert hash_index.has_file(file_path)

    hash_index.remove_file(file_path)
    assert not hash_index.has_file(file_path)


def test_hash_index_list_files(hash_index, sample_files):
    """Test listing all indexed files."""
    # Add multiple files
    for file_path in sample_files:
        hash_index.add_file(file_path)

    indexed_files = hash_index.list_files()

    assert len(indexed_files) == len(sample_files)
    for file_path in sample_files:
        assert str(file_path) in indexed_files


def test_hash_index_persistence(temp_index_file, sample_files):
    """Test that index persists to disk."""
    # Create index and add files
    index1 = FileHashIndex(index_path=temp_index_file)
    for file_path in sample_files:
        index1.add_file(file_path)

    count1 = len(index1.list_files())

    # Save and close
    index1.save()
    del index1

    # Load in new instance
    index2 = FileHashIndex(index_path=temp_index_file)
    count2 = len(index2.list_files())

    assert count1 == count2
    assert count2 == len(sample_files)


def test_hash_index_clear(hash_index, sample_files):
    """Test clearing entire index."""
    # Add files
    for file_path in sample_files:
        hash_index.add_file(file_path)

    assert len(hash_index.list_files()) == len(sample_files)

    # Clear
    hash_index.clear()

    assert len(hash_index.list_files()) == 0


def test_hash_index_get_stats(hash_index, sample_files):
    """Test getting index statistics."""
    for file_path in sample_files:
        hash_index.add_file(file_path)

    stats = hash_index.get_stats()

    assert stats["total_files"] == len(sample_files)
    assert "index_path" in stats
    assert "index_size_bytes" in stats


def test_hash_index_handles_missing_file(hash_index):
    """Test handling of missing files."""
    missing_file = Path("/nonexistent/file.txt")

    # Should return None or handle gracefully
    result = hash_index.has_file(missing_file)
    assert result is False


def test_hash_index_update_file(hash_index, tmp_path):
    """Test updating file hash when content changes."""
    file_path = tmp_path / "doc.txt"
    file_path.write_text("Original content")

    # Add to index
    hash_index.add_file(file_path)
    original_hash = hash_index.get_hash(file_path)

    # Modify file
    file_path.write_text("New content")

    # Update index
    hash_index.update_file(file_path)
    new_hash = hash_index.get_hash(file_path)

    assert new_hash != original_hash
    assert not hash_index.has_changed(file_path)  # After update, no change detected
