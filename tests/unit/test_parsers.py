from pathlib import Path
import pytest
from vast_rag.parsers.markdown import MarkdownParser
from vast_rag.types import ParsedDocument


@pytest.fixture
def sample_markdown(tmp_path):
    """Create a sample markdown file."""
    md_file = tmp_path / "sample.md"
    content = """# Main Title

## Section 1

This is section 1 content.

## Section 2

This is section 2 content.

### Subsection 2.1

Nested content here.
"""
    md_file.write_text(content)
    return md_file


def test_markdown_parser_basic(sample_markdown):
    """Test basic markdown parsing."""
    parser = MarkdownParser()
    doc = parser.parse(sample_markdown)

    assert isinstance(doc, ParsedDocument)
    assert doc.format == "markdown"
    assert doc.source_path == sample_markdown
    assert "Main Title" in doc.text
    assert "Section 1" in doc.text


def test_markdown_parser_extracts_sections(sample_markdown):
    """Test that sections are extracted from headers."""
    parser = MarkdownParser()
    doc = parser.parse(sample_markdown)

    sections = doc.sections
    assert "Main Title" in sections
    assert "Section 1" in sections
    assert "Section 2" in sections
    assert "Subsection 2.1" in sections
