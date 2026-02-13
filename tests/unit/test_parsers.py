from pathlib import Path
import pytest
from vast_rag.parsers.markdown import MarkdownParser
from vast_rag.parsers.pdf import PDFParser
from vast_rag.types import ParsedDocument
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


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


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file."""
    pdf_file = tmp_path / "sample.pdf"

    # Create a simple 2-page PDF
    c = canvas.Canvas(str(pdf_file), pagesize=letter)

    # Page 1
    c.drawString(100, 750, "Page 1 Title")
    c.drawString(100, 700, "This is content on page 1.")
    c.showPage()

    # Page 2
    c.drawString(100, 750, "Page 2 Title")
    c.drawString(100, 700, "This is content on page 2.")
    c.showPage()

    c.save()
    return pdf_file


def test_pdf_parser_extracts_pages(sample_pdf):
    """Test PDF parsing extracts page numbers."""
    parser = PDFParser()
    doc = parser.parse(sample_pdf)

    assert doc.format == "pdf"
    assert doc.pages == 2
    assert "Page 1 Title" in doc.text
    assert "Page 2 Title" in doc.text


def test_pdf_parser_page_mapping(sample_pdf):
    """Test that page numbers are tracked in metadata."""
    parser = PDFParser()
    doc = parser.parse(sample_pdf)

    page_texts = doc.metadata["page_texts"]
    assert len(page_texts) == 2
    assert "Page 1 Title" in page_texts[0]
    assert "Page 2 Title" in page_texts[1]
