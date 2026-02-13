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
