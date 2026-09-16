"""
Physical PDF Loader and Text Extractor (PyMuPDF Engine).
Extracts clean text while strictly binding original page numbers without chunking or vector operations.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import pymupdf as fitz


@dataclass
class ExtractedPage:
    """Represents an extracted document page with text and metadata."""
    doc_id: str
    file_name: str
    page_number: int
    total_pages: int
    text: str


class PDFDocumentLoader:
    """Loader and processor for single or batch PDF documents."""

    def __init__(self, min_char_threshold: int = 15):
        """
        Args:
            min_char_threshold: Minimum character count to qualify as a valid content page.
        """
        self.min_char_threshold = min_char_threshold

    @staticmethod
    def _generate_doc_id(file_path: Path) -> str:
        """Generate a unique document ID based on file name and size."""
        unique_str = f"{file_path.name}_{file_path.stat().st_size}"
        return hashlib.md5(unique_str.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespaces and line breaks while preserving multilingual characters."""
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def load_single_pdf(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        """Extract a list of pages from a given PDF file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found at: {path}")

        doc_id = self._generate_doc_id(path)
        extracted_pages: List[ExtractedPage] = []

        try:
            with fitz.open(path) as doc:
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    page = doc[page_idx]
                    raw_text = page.get_text("text")
                    cleaned_text = self._clean_text(raw_text)

                    if len(cleaned_text) >= self.min_char_threshold:
                        extracted_pages.append(
                            ExtractedPage(
                                doc_id=doc_id,
                                file_name=path.name,
                                page_number=page_idx + 1,
                                total_pages=total_pages,
                                text=cleaned_text,
                            )
                        )
        except Exception as e:
            raise RuntimeError(f"Error reading PDF file '{path.name}': {str(e)}") from e

        return extracted_pages

    def load_multiple_pdfs(self, file_paths: List[Union[str, Path]]) -> List[ExtractedPage]:
        """
        Extract text from multiple PDF files simultaneously.
        """
        all_pages: List[ExtractedPage] = []
        for file_path in file_paths:
            pages = self.load_single_pdf(file_path)
            all_pages.extend(pages)
        return all_pages
