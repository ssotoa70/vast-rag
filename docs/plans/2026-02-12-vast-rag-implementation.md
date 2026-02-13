# VAST RAG System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MCP server that automatically indexes technical documentation with vector embeddings, enabling fast semantic search with citation tracking.

**Architecture:** Python MCP server with embedded file watcher (watchdog), multi-format document parser, local embeddings (sentence-transformers), and ChromaDB vector storage. Two-collection design separates VAST Data docs from general technical docs.

**Tech Stack:** Python 3.11+, MCP SDK, ChromaDB, sentence-transformers, watchdog, PyPDF2, pdfplumber, python-docx, BeautifulSoup4

---

## Task 1: Project Setup & Dependencies

**Files:**
- Create: `vast-rag/pyproject.toml`
- Create: `vast-rag/README.md`
- Create: `vast-rag/src/vast_rag/__init__.py`
- Create: `vast-rag/.gitignore`

**Step 1: Create project directory structure**

Run:
```bash
mkdir -p vast-rag/src/vast_rag/{core,parsers,mcp}
mkdir -p vast-rag/tests/{unit,integration,fixtures}
mkdir -p vast-rag/docs
cd vast-rag
```

Expected: Directories created

**Step 2: Write pyproject.toml**

Create `pyproject.toml`:
```toml
[project]
name = "vast-rag"
version = "0.1.0"
description = "MCP server for semantic search over VAST Data documentation"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "chromadb>=0.4.22",
    "sentence-transformers>=2.3.1",
    "watchdog>=3.0.0",
    "PyPDF2>=3.0.0",
    "pdfplumber>=0.10.0",
    "python-docx>=1.1.0",
    "beautifulsoup4>=4.12.0",
    "markdown>=3.5.0",
    "tiktoken>=0.5.2",
    "pydantic>=2.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.12.0",
    "ruff>=0.1.9",
    "mypy>=1.8.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --cov=src/vast_rag --cov-report=term-missing"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
```

**Step 3: Write .gitignore**

Create `.gitignore`:
```
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.venv/
venv/
.mypy_cache/
.ruff_cache/
*.log
.DS_Store
```

**Step 4: Install dependencies**

Run:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: All dependencies installed successfully

**Step 5: Verify installation**

Run:
```bash
python -c "import chromadb; import sentence_transformers; import watchdog; print('✓ All imports successful')"
```

Expected: `✓ All imports successful`

**Step 6: Commit initial setup**

Run:
```bash
git init
git add .
git commit -m "feat: initial project setup with dependencies

- Add pyproject.toml with all required dependencies
- Create directory structure for MCP server
- Add .gitignore for Python projects"
```

---

## Task 2: Configuration & Types

**Files:**
- Create: `vast-rag/src/vast_rag/config.py`
- Create: `vast-rag/src/vast_rag/types.py`
- Create: `vast-rag/tests/unit/test_config.py`

**Step 1: Write test for configuration loading**

Create `tests/unit/test_config.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'vast_rag.config'"

**Step 3: Write types module**

Create `src/vast_rag/types.py`:
```python
"""Type definitions for VAST RAG system."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class ParsedDocument:
    """Represents a parsed document with extracted text and metadata."""

    text: str
    metadata: dict
    format: str
    source_path: Path

    @property
    def pages(self) -> int:
        """Number of pages in the document."""
        return self.metadata.get("pages", 1)

    @property
    def sections(self) -> list[str]:
        """Section headers found in the document."""
        return self.metadata.get("sections", [])


@dataclass
class DocumentChunk:
    """A chunk of text from a document with metadata."""

    text: str
    metadata: dict
    chunk_index: int

    @property
    def source_file(self) -> str:
        """Original source file name."""
        return self.metadata["source_file"]

    @property
    def page_number(self) -> int | None:
        """Page number this chunk came from."""
        return self.metadata.get("page_number")

    @property
    def section(self) -> str | None:
        """Section header this chunk belongs to."""
        return self.metadata.get("section")


@dataclass
class SearchResult:
    """A search result with text, metadata, and similarity score."""

    text: str
    source: str
    page: int | None
    section: str | None
    score: float
    category: Literal["vast-data", "general-tech"]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "source": self.source,
            "page": self.page,
            "section": self.section,
            "score": round(self.score, 3),
            "category": self.category,
        }


CollectionName = Literal["vast_data_collection", "general_tech_collection"]
```

**Step 4: Write config module**

Create `src/vast_rag/config.py`:
```python
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
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -v`

Expected: PASS (3 tests)

**Step 6: Commit configuration layer**

Run:
```bash
git add src/vast_rag/config.py src/vast_rag/types.py tests/unit/test_config.py
git commit -m "feat: add configuration and type definitions

- Add Config class with environment variable support
- Add type definitions for documents, chunks, and search results
- Add unit tests for configuration validation"
```

---

## Task 3: Document Parser - Markdown & Text

**Files:**
- Create: `vast-rag/src/vast_rag/parsers/base.py`
- Create: `vast-rag/src/vast_rag/parsers/markdown.py`
- Create: `vast-rag/src/vast_rag/parsers/text.py`
- Create: `vast-rag/tests/unit/test_parsers.py`
- Create: `vast-rag/tests/fixtures/sample.md`

**Step 1: Write test for markdown parser**

Create `tests/unit/test_parsers.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_parsers.py::test_markdown_parser_basic -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'vast_rag.parsers'"

**Step 3: Write base parser interface**

Create `src/vast_rag/parsers/base.py`:
```python
"""Base parser interface."""
from abc import ABC, abstractmethod
from pathlib import Path
from vast_rag.types import ParsedDocument


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document and return structured content.

        Args:
            file_path: Path to the document file

        Returns:
            ParsedDocument with extracted text and metadata

        Raises:
            ValueError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if this parser can handle the file
        """
        pass
```

**Step 4: Write markdown parser implementation**

Create `src/vast_rag/parsers/markdown.py`:
```python
"""Markdown document parser."""
import re
from pathlib import Path
import markdown
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class MarkdownParser(BaseParser):
    """Parser for Markdown documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is markdown."""
        return file_path.suffix.lower() in {".md", ".markdown"}

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse markdown file and extract sections."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: not a markdown file")

        content = file_path.read_text(encoding="utf-8")

        # Extract section headers
        sections = self._extract_sections(content)

        # Convert to plain text (strip markdown syntax)
        text = markdown.markdown(content)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        metadata = {
            "sections": sections,
            "pages": 1,  # Markdown doesn't have pages
            "format": "markdown",
        }

        return ParsedDocument(
            text=text.strip(),
            metadata=metadata,
            format="markdown",
            source_path=file_path,
        )

    def _extract_sections(self, content: str) -> list[str]:
        """Extract section headers from markdown."""
        # Match markdown headers (# Header)
        header_pattern = r'^#{1,6}\s+(.+)$'
        headers = re.findall(header_pattern, content, re.MULTILINE)
        return [h.strip() for h in headers]
```

**Step 5: Write text parser implementation**

Create `src/vast_rag/parsers/text.py`:
```python
"""Plain text document parser."""
from pathlib import Path
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class TextParser(BaseParser):
    """Parser for plain text documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is plain text or code."""
        return file_path.suffix.lower() in {
            ".txt", ".py", ".js", ".java", ".json", ".yaml", ".yml", ".sh", ".bash"
        }

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse text file."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: unsupported extension")

        content = file_path.read_text(encoding="utf-8")

        metadata = {
            "sections": [],
            "pages": 1,
            "format": "text",
            "extension": file_path.suffix,
        }

        return ParsedDocument(
            text=content.strip(),
            metadata=metadata,
            format="text",
            source_path=file_path,
        )
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_parsers.py -v`

Expected: PASS (2 tests)

**Step 7: Commit markdown and text parsers**

Run:
```bash
git add src/vast_rag/parsers/ tests/unit/test_parsers.py
git commit -m "feat: add markdown and text parsers

- Add BaseParser interface for document parsers
- Implement MarkdownParser with section extraction
- Implement TextParser for code and plain text files
- Add unit tests for parsing functionality"
```

---

## Task 4: Document Parser - PDF

**Files:**
- Create: `vast-rag/src/vast_rag/parsers/pdf.py`
- Update: `vast-rag/tests/unit/test_parsers.py`

**Step 1: Write test for PDF parser**

Add to `tests/unit/test_parsers.py`:
```python
from vast_rag.parsers.pdf import PDFParser
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


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
```

**Step 2: Install reportlab for tests**

Add to `pyproject.toml` under `[project.optional-dependencies]`:
```toml
dev = [
    # ... existing deps ...
    "reportlab>=4.0.0",
]
```

Run: `pip install reportlab`

**Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_parsers.py::test_pdf_parser_extracts_pages -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'vast_rag.parsers.pdf'"

**Step 4: Write PDF parser with PyPDF2**

Create `src/vast_rag/parsers/pdf.py`:
```python
"""PDF document parser with fallback handling."""
import logging
from pathlib import Path
from PyPDF2 import PdfReader
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """Parser for PDF documents with pdfplumber fallback."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is PDF."""
        return file_path.suffix.lower() == ".pdf"

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse PDF and extract text with page numbers."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: not a PDF file")

        try:
            return self._parse_with_pypdf2(file_path)
        except Exception as e:
            logger.warning(f"PyPDF2 failed for {file_path}: {e}. Trying pdfplumber...")
            return self._parse_with_pdfplumber(file_path)

    def _parse_with_pypdf2(self, file_path: Path) -> ParsedDocument:
        """Parse PDF using PyPDF2."""
        reader = PdfReader(str(file_path))
        page_texts = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                page_texts.append(text.strip())

        # Combine all pages
        full_text = "\n\n".join(page_texts)

        metadata = {
            "pages": len(page_texts),
            "page_texts": page_texts,  # Keep per-page text for chunking
            "sections": [],  # PDF doesn't have structured sections
            "format": "pdf",
            "partial_parse": False,
        }

        return ParsedDocument(
            text=full_text.strip(),
            metadata=metadata,
            format="pdf",
            source_path=file_path,
        )

    def _parse_with_pdfplumber(self, file_path: Path) -> ParsedDocument:
        """Fallback parser using pdfplumber for complex layouts."""
        try:
            import pdfplumber
        except ImportError:
            raise ValueError("pdfplumber not installed, cannot parse complex PDFs")

        page_texts = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    page_texts.append(text.strip())

        full_text = "\n\n".join(page_texts)

        metadata = {
            "pages": len(page_texts),
            "page_texts": page_texts,
            "sections": [],
            "format": "pdf",
            "partial_parse": False,
            "parser": "pdfplumber",
        }

        return ParsedDocument(
            text=full_text.strip(),
            metadata=metadata,
            format="pdf",
            source_path=file_path,
        )
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_parsers.py -k pdf -v`

Expected: PASS (2 PDF tests)

**Step 6: Commit PDF parser**

Run:
```bash
git add src/vast_rag/parsers/pdf.py tests/unit/test_parsers.py pyproject.toml
git commit -m "feat: add PDF parser with fallback

- Implement PDFParser using PyPDF2 as primary
- Add pdfplumber fallback for complex layouts
- Extract per-page text for accurate page citations
- Add tests with reportlab-generated PDFs"
```

---

## Task 5: Document Parser - HTML & DOCX

**Files:**
- Create: `vast-rag/src/vast_rag/parsers/html.py`
- Create: `vast-rag/src/vast_rag/parsers/docx.py`
- Update: `vast-rag/tests/unit/test_parsers.py`

**Step 1: Write test for HTML parser**

Add to `tests/unit/test_parsers.py`:
```python
from vast_rag.parsers.html import HTMLParser


@pytest.fixture
def sample_html(tmp_path):
    """Create a sample HTML file."""
    html_file = tmp_path / "sample.html"
    content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Document</title></head>
    <body>
        <h1>Main Heading</h1>
        <p>This is a paragraph.</p>
        <h2>Subheading</h2>
        <p>More content here.</p>
        <script>console.log('ignore this');</script>
    </body>
    </html>
    """
    html_file.write_text(content)
    return html_file


def test_html_parser_strips_tags(sample_html):
    """Test HTML parsing removes tags but keeps text."""
    parser = HTMLParser()
    doc = parser.parse(sample_html)

    assert doc.format == "html"
    assert "Main Heading" in doc.text
    assert "<h1>" not in doc.text
    assert "<script>" not in doc.text
    assert "console.log" not in doc.text  # Script removed


def test_html_parser_extracts_headings(sample_html):
    """Test that HTML headings are extracted."""
    parser = HTMLParser()
    doc = parser.parse(sample_html)

    assert "Main Heading" in doc.sections
    assert "Subheading" in doc.sections
```

**Step 2: Write test for DOCX parser**

Add to `tests/unit/test_parsers.py`:
```python
from vast_rag.parsers.docx import DOCXParser
from docx import Document


@pytest.fixture
def sample_docx(tmp_path):
    """Create a sample DOCX file."""
    docx_file = tmp_path / "sample.docx"

    doc = Document()
    doc.add_heading("Main Title", level=1)
    doc.add_paragraph("First paragraph content.")
    doc.add_heading("Section 1", level=2)
    doc.add_paragraph("Section 1 content.")

    doc.save(str(docx_file))
    return docx_file


def test_docx_parser_extracts_text(sample_docx):
    """Test DOCX parsing extracts all text."""
    parser = DOCXParser()
    doc = parser.parse(sample_docx)

    assert doc.format == "docx"
    assert "Main Title" in doc.text
    assert "First paragraph content" in doc.text
    assert "Section 1" in doc.text


def test_docx_parser_preserves_headings(sample_docx):
    """Test that DOCX headings are extracted."""
    parser = DOCXParser()
    doc = parser.parse(sample_docx)

    assert "Main Title" in doc.sections
    assert "Section 1" in doc.sections
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_parsers.py -k "html or docx" -v`

Expected: FAIL with missing modules

**Step 4: Write HTML parser**

Create `src/vast_rag/parsers/html.py`:
```python
"""HTML document parser."""
from pathlib import Path
from bs4 import BeautifulSoup
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class HTMLParser(BaseParser):
    """Parser for HTML documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is HTML."""
        return file_path.suffix.lower() in {".html", ".htm"}

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse HTML and extract text content."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: not an HTML file")

        content = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style tags
        for element in soup(["script", "style"]):
            element.decompose()

        # Extract headings
        sections = []
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            sections.append(heading.get_text(strip=True))

        # Get text content
        text = soup.get_text(separator="\n", strip=True)

        metadata = {
            "sections": sections,
            "pages": 1,
            "format": "html",
        }

        return ParsedDocument(
            text=text,
            metadata=metadata,
            format="html",
            source_path=file_path,
        )
```

**Step 5: Write DOCX parser**

Create `src/vast_rag/parsers/docx.py`:
```python
"""DOCX document parser."""
from pathlib import Path
from docx import Document
from vast_rag.parsers.base import BaseParser
from vast_rag.types import ParsedDocument


class DOCXParser(BaseParser):
    """Parser for Microsoft Word DOCX documents."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is DOCX."""
        return file_path.suffix.lower() == ".docx"

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse DOCX and extract text with heading structure."""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse {file_path}: not a DOCX file")

        doc = Document(str(file_path))

        paragraphs = []
        sections = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Check if paragraph is a heading
            if para.style.name.startswith("Heading"):
                sections.append(text)

            paragraphs.append(text)

        full_text = "\n\n".join(paragraphs)

        metadata = {
            "sections": sections,
            "pages": 1,  # DOCX doesn't expose page count easily
            "format": "docx",
        }

        return ParsedDocument(
            text=full_text,
            metadata=metadata,
            format="docx",
            source_path=file_path,
        )
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_parsers.py -k "html or docx" -v`

Expected: PASS (4 tests)

**Step 7: Commit HTML and DOCX parsers**

Run:
```bash
git add src/vast_rag/parsers/html.py src/vast_rag/parsers/docx.py tests/unit/test_parsers.py
git commit -m "feat: add HTML and DOCX parsers

- Implement HTMLParser with BeautifulSoup
- Strip script/style tags from HTML
- Implement DOCXParser with heading extraction
- Add tests for both formats"
```

---

## Task 6: Parser Factory

**Files:**
- Create: `vast-rag/src/vast_rag/parsers/factory.py`
- Update: `vast-rag/tests/unit/test_parsers.py`

**Step 1: Write test for parser factory**

Add to `tests/unit/test_parsers.py`:
```python
from vast_rag.parsers.factory import ParserFactory


def test_parser_factory_selects_correct_parser(sample_markdown, sample_pdf, sample_html):
    """Test factory selects appropriate parser for each format."""
    factory = ParserFactory()

    md_parser = factory.get_parser(sample_markdown)
    assert md_parser.__class__.__name__ == "MarkdownParser"

    pdf_parser = factory.get_parser(sample_pdf)
    assert pdf_parser.__class__.__name__ == "PDFParser"

    html_parser = factory.get_parser(sample_html)
    assert html_parser.__class__.__name__ == "HTMLParser"


def test_parser_factory_raises_for_unsupported(tmp_path):
    """Test factory raises error for unsupported formats."""
    factory = ParserFactory()
    unsupported = tmp_path / "file.exe"
    unsupported.write_bytes(b"binary data")

    with pytest.raises(ValueError, match="No parser available"):
        factory.get_parser(unsupported)


def test_parser_factory_parse_document(sample_markdown):
    """Test factory can parse documents directly."""
    factory = ParserFactory()
    doc = factory.parse_document(sample_markdown)

    assert doc.format == "markdown"
    assert "Main Title" in doc.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_parsers.py::test_parser_factory_selects_correct_parser -v`

Expected: FAIL with "No module named 'vast_rag.parsers.factory'"

**Step 3: Write parser factory**

Create `src/vast_rag/parsers/factory.py`:
```python
"""Factory for selecting appropriate document parser."""
import logging
from pathlib import Path
from typing import Type

from vast_rag.parsers.base import BaseParser
from vast_rag.parsers.markdown import MarkdownParser
from vast_rag.parsers.text import TextParser
from vast_rag.parsers.pdf import PDFParser
from vast_rag.parsers.html import HTMLParser
from vast_rag.parsers.docx import DOCXParser
from vast_rag.types import ParsedDocument

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating appropriate document parsers."""

    def __init__(self):
        """Initialize factory with all available parsers."""
        self._parsers: list[Type[BaseParser]] = [
            PDFParser,
            DOCXParser,
            HTMLParser,
            MarkdownParser,
            TextParser,  # Keep text parser last as fallback
        ]

    def get_parser(self, file_path: Path) -> BaseParser:
        """Get appropriate parser for the file.

        Args:
            file_path: Path to the file

        Returns:
            Parser instance that can handle the file

        Raises:
            ValueError: If no parser can handle the file
        """
        for parser_class in self._parsers:
            parser = parser_class()
            if parser.can_parse(file_path):
                logger.debug(f"Selected {parser_class.__name__} for {file_path}")
                return parser

        raise ValueError(
            f"No parser available for {file_path}. "
            f"Supported extensions: .pdf, .docx, .html, .md, .txt, code files"
        )

    def parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse a document using the appropriate parser.

        Args:
            file_path: Path to the document

        Returns:
            ParsedDocument with extracted content

        Raises:
            ValueError: If file cannot be parsed
        """
        parser = self.get_parser(file_path)
        return parser.parse(file_path)
```

**Step 4: Update __init__.py to export factory**

Update `src/vast_rag/parsers/__init__.py`:
```python
"""Document parsers for various file formats."""
from vast_rag.parsers.factory import ParserFactory

__all__ = ["ParserFactory"]
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_parsers.py -k factory -v`

Expected: PASS (3 tests)

**Step 6: Commit parser factory**

Run:
```bash
git add src/vast_rag/parsers/factory.py src/vast_rag/parsers/__init__.py tests/unit/test_parsers.py
git commit -m "feat: add parser factory for format detection

- Create ParserFactory to select appropriate parser
- Support all document formats (PDF, DOCX, HTML, MD, text)
- Add tests for parser selection and unsupported formats"
```

---

## Task 7: Chunking Strategy

**Files:**
- Create: `vast-rag/src/vast_rag/core/chunker.py`
- Create: `vast-rag/tests/unit/test_chunker.py`

**Step 1: Write test for chunking**

Create `tests/unit/test_chunker.py`:
```python
import pytest
from vast_rag.core.chunker import SemanticChunker
from vast_rag.types import ParsedDocument, DocumentChunk
from pathlib import Path


@pytest.fixture
def long_document():
    """Create a long document for chunking."""
    # Create text that's ~1500 tokens (will be split into 3 chunks of 500)
    text = " ".join([f"Word{i}" for i in range(2000)])  # Approx 2000 tokens

    metadata = {
        "sections": ["Section 1", "Section 2"],
        "pages": 1,
        "format": "text",
    }

    return ParsedDocument(
        text=text,
        metadata=metadata,
        format="text",
        source_path=Path("test.txt"),
    )


def test_chunker_creates_chunks_with_overlap(long_document):
    """Test chunking creates overlapping chunks."""
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_document(long_document, category="general-tech")

    assert len(chunks) > 1  # Should create multiple chunks

    # Check overlap exists between consecutive chunks
    for i in range(len(chunks) - 1):
        chunk1_end = chunks[i].text[-100:]  # Last part of chunk
        chunk2_start = chunks[i + 1].text[:100]  # Start of next chunk
        # Should have some overlap
        assert len(set(chunk1_end.split()) & set(chunk2_start.split())) > 0


def test_chunker_preserves_metadata(long_document):
    """Test that metadata is preserved in chunks."""
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_document(long_document, category="vast-data")

    for idx, chunk in enumerate(chunks):
        assert chunk.metadata["source_file"] == "test.txt"
        assert chunk.metadata["category"] == "vast-data"
        assert chunk.chunk_index == idx


def test_chunker_respects_token_limits():
    """Test chunks don't exceed token limit."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=10)

    text = " ".join([f"Word{i}" for i in range(500)])
    doc = ParsedDocument(
        text=text,
        metadata={"sections": [], "pages": 1, "format": "text"},
        format="text",
        source_path=Path("test.txt"),
    )

    chunks = chunker.chunk_document(doc, category="general-tech")

    # Each chunk should be approximately chunk_size tokens
    for chunk in chunks:
        token_count = len(chunk.text.split())  # Rough token count
        assert token_count <= 120  # Some margin for token counting differences
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_chunker.py -v`

Expected: FAIL with "No module named 'vast_rag.core.chunker'"

**Step 3: Write chunker implementation**

Create `src/vast_rag/core/chunker.py`:
```python
"""Semantic chunking for documents."""
import logging
from typing import Literal
import tiktoken
from vast_rag.types import ParsedDocument, DocumentChunk

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Chunks documents semantically with overlap."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize chunker.

        Args:
            chunk_size: Target tokens per chunk
            chunk_overlap: Overlap tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk_document(
        self,
        document: ParsedDocument,
        category: Literal["vast-data", "general-tech"],
    ) -> list[DocumentChunk]:
        """Chunk a document into smaller pieces.

        Args:
            document: Parsed document to chunk
            category: Document category for metadata

        Returns:
            List of document chunks with metadata
        """
        # For PDFs, chunk by page first if available
        if document.format == "pdf" and "page_texts" in document.metadata:
            return self._chunk_pdf(document, category)

        # For other formats, chunk the full text
        return self._chunk_text(
            text=document.text,
            source_file=document.source_path.name,
            category=category,
            sections=document.sections,
        )

    def _chunk_pdf(
        self,
        document: ParsedDocument,
        category: Literal["vast-data", "general-tech"],
    ) -> list[DocumentChunk]:
        """Chunk PDF by pages to preserve page numbers."""
        chunks = []
        chunk_index = 0

        page_texts = document.metadata["page_texts"]

        for page_num, page_text in enumerate(page_texts, start=1):
            # Chunk each page
            page_chunks = self._chunk_text(
                text=page_text,
                source_file=document.source_path.name,
                category=category,
                sections=document.sections,
                page_number=page_num,
            )

            # Update chunk indices
            for chunk in page_chunks:
                chunk.chunk_index = chunk_index
                chunk_index += 1

            chunks.extend(page_chunks)

        return chunks

    def _chunk_text(
        self,
        text: str,
        source_file: str,
        category: Literal["vast-data", "general-tech"],
        sections: list[str],
        page_number: int | None = None,
    ) -> list[DocumentChunk]:
        """Chunk text with overlap.

        Args:
            text: Text to chunk
            source_file: Source filename
            category: Document category
            sections: Section headers from document
            page_number: Optional page number

        Returns:
            List of chunks
        """
        # Tokenize
        tokens = self._tokenizer.encode(text)

        if len(tokens) <= self.chunk_size:
            # Document fits in one chunk
            metadata = {
                "source_file": source_file,
                "category": category,
                "page_number": page_number,
                "section": sections[0] if sections else None,
            }
            return [
                DocumentChunk(
                    text=text,
                    metadata=metadata,
                    chunk_index=0,
                )
            ]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(tokens):
            # Get chunk with overlap
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]

            # Decode back to text
            chunk_text = self._tokenizer.decode(chunk_tokens)

            metadata = {
                "source_file": source_file,
                "category": category,
                "page_number": page_number,
                "section": self._find_section(chunk_text, sections),
            }

            chunks.append(
                DocumentChunk(
                    text=chunk_text.strip(),
                    metadata=metadata,
                    chunk_index=chunk_index,
                )
            )

            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            chunk_index += 1

        return chunks

    def _find_section(self, text: str, sections: list[str]) -> str | None:
        """Find which section this text belongs to."""
        for section in sections:
            if section in text:
                return section
        return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_chunker.py -v`

Expected: PASS (3 tests)

**Step 5: Commit chunker**

Run:
```bash
git add src/vast_rag/core/chunker.py tests/unit/test_chunker.py
git commit -m "feat: add semantic chunking with overlap

- Implement SemanticChunker with tiktoken
- Support chunk_size and chunk_overlap configuration
- Special handling for PDFs to preserve page numbers
- Metadata preservation in all chunks
- Add comprehensive unit tests"
```

---

*Due to length constraints, I'll continue with the remaining tasks in a summary format. The plan would continue with:*

**Task 8:** Embedding Service (sentence-transformers, caching, batch processing)
**Task 9:** ChromaDB Manager (collections, CRUD, persistence)
**Task 10:** File Watcher (watchdog, debouncing, categorization)
**Task 11:** File Hash Index (tracking processed files)
**Task 12:** MCP Server Implementation (tools: search_docs, list_collections, get_document)
**Task 13:** Integration (wire all components together)
**Task 14:** End-to-End Testing
**Task 15:** Deployment & Configuration

Each following the same TDD pattern: test → fail → implement → pass → commit.

Would you like me to continue with the complete plan, or would this sample be sufficient to demonstrate the structure?

`★ Insight ─────────────────────────────────────`
**Bite-sized TDD workflow**: Each task breaks into 5-10 minute steps with explicit test-first development. The pattern (write test → verify failure → implement → verify pass → commit) creates a safety net and documentation trail. This granularity makes it easy to pause/resume work and prevents "big bang" integration failures.
`─────────────────────────────────────────────────`