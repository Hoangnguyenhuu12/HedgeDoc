"""
Multi-Format Document Loader and Text Extractor.
Supports PDF (PyMuPDF), Word (.docx via python-docx), and Excel (.xlsx/.xls via pandas/openpyxl).
Extracts clean text while strictly binding original page/section/sheet locations for citations.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Optional
import pymupdf as fitz


@dataclass
class ExtractedPage:
    """Represents an extracted document page or section with text and location metadata."""
    doc_id: str
    file_name: str
    page_number: int
    total_pages: int
    text: str
    location_label: Optional[str] = None


class BaseDocumentLoader:
    """Base utilities shared across all format loaders."""

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


class PDFDocumentLoader(BaseDocumentLoader):
    """Loader and processor for PDF documents using PyMuPDF."""

    def __init__(self, min_char_threshold: int = 15):
        self.min_char_threshold = min_char_threshold

    def load_single_pdf(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        """Extract pages from a PDF file."""
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
                                text=f"# Tài liệu: {path.name} (Trang {page_idx + 1})\n\n{cleaned_text}",
                                location_label=f"Trang {page_idx + 1}"
                            )
                        )
        except Exception as e:
            raise RuntimeError(f"Error reading PDF file '{path.name}': {str(e)}") from e

        return extracted_pages

    def load_multiple_pdfs(self, file_paths: List[Union[str, Path]]) -> List[ExtractedPage]:
        """Extract text from multiple PDF files."""
        all_pages: List[ExtractedPage] = []
        for file_path in file_paths:
            all_pages.extend(self.load_single_pdf(file_path))
        return all_pages


class DocxDocumentLoader(BaseDocumentLoader):
    """Loader and processor for Microsoft Word (.docx) documents."""

    def __init__(self, min_char_threshold: int = 15, max_section_chars: int = 1500):
        self.min_char_threshold = min_char_threshold
        self.max_section_chars = max_section_chars

    def load_single_docx(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        """Extract structured sections and tables from a .docx file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found at: {path}")

        import docx

        doc_id = self._generate_doc_id(path)
        extracted_pages: List[ExtractedPage] = []

        try:
            doc = docx.Document(path)
            sections: List[dict] = []
            current_heading = "Mở đầu / Giới thiệu"
            current_paragraphs: List[str] = []

            def flush_section():
                nonlocal current_paragraphs
                if current_paragraphs:
                    combined = "\n\n".join(current_paragraphs)
                    cleaned = self._clean_text(combined)
                    if len(cleaned) >= self.min_char_threshold:
                        sections.append({
                            "heading": current_heading,
                            "text": cleaned
                        })
                    current_paragraphs = []

            # Process paragraphs and collect by headings
            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue

                # Detect headings
                if p.style.name.startswith("Heading") or p.style.name in ["Title", "Subtitle"]:
                    flush_section()
                    current_heading = text
                else:
                    current_paragraphs.append(text)
                    # Split if section becomes excessively long
                    if sum(len(x) for x in current_paragraphs) >= self.max_section_chars:
                        flush_section()

            flush_section()

            # Process Word Tables
            for idx, table in enumerate(doc.tables, start=1):
                table_lines = []
                for row in table.rows:
                    row_cells = [self._clean_text(cell.text) for cell in row.cells]
                    # remove duplicates caused by merged cells
                    cleaned_cells = []
                    for c in row_cells:
                        if not cleaned_cells or c != cleaned_cells[-1]:
                            cleaned_cells.append(c)
                    table_lines.append(" | ".join(cleaned_cells))

                if table_lines:
                    table_text = f"### Bảng {idx}\n" + "\n".join(table_lines)
                    sections.append({
                        "heading": f"Bảng {idx}",
                        "text": table_text
                    })

            total_sections = max(1, len(sections))
            for s_idx, sec in enumerate(sections, start=1):
                extracted_pages.append(
                    ExtractedPage(
                        doc_id=doc_id,
                        file_name=path.name,
                        page_number=s_idx,
                        total_pages=total_sections,
                        text=f"# Tài liệu: {path.name}\n## {sec['heading']}\n\n{sec['text']}",
                        location_label=f"Mục {s_idx}: {sec['heading']}"
                    )
                )

        except Exception as e:
            raise RuntimeError(f"Error reading Word (.docx) file '{path.name}': {str(e)}") from e

        return extracted_pages


class ExcelDocumentLoader(BaseDocumentLoader):
    """Loader and processor for Excel spreadsheets (.xlsx, .xls)."""

    def __init__(self, rows_per_chunk: int = 15, min_char_threshold: int = 15):
        self.rows_per_chunk = rows_per_chunk
        self.min_char_threshold = min_char_threshold

    def load_single_excel(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        """Extract sheets and convert rows into structured Markdown tables."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found at: {path}")

        import pandas as pd

        doc_id = self._generate_doc_id(path)
        extracted_pages: List[ExtractedPage] = []

        try:
            # Read all sheets into dictionary
            excel_data = pd.read_excel(path, sheet_name=None)
            sheet_blocks: List[dict] = []

            for sheet_name, df in excel_data.items():
                if df.empty:
                    continue

                # Drop rows that are completely NaN
                df = df.dropna(how="all")
                if df.empty:
                    continue

                # Fill remaining NaN with empty string
                df = df.fillna("")
                total_rows = len(df)

                # Chunk rows in batches
                for start_row in range(0, total_rows, self.rows_per_chunk):
                    end_row = min(start_row + self.rows_per_chunk, total_rows)
                    sub_df = df.iloc[start_row:end_row]

                    # Convert to markdown table format
                    try:
                        md_table = sub_df.to_markdown(index=False)
                    except Exception:
                        # Fallback text representation if tabulate is unavailable
                        headers = " | ".join(str(c) for c in sub_df.columns)
                        rows_txt = [" | ".join(str(val) for val in row) for row in sub_df.values]
                        md_table = headers + "\n" + "-" * len(headers) + "\n" + "\n".join(rows_txt)

                    block_text = f"# Tài liệu: {path.name}\n### Sheet: {sheet_name} (Dòng {start_row + 1} - {end_row})\n\n{md_table}"
                    sheet_blocks.append({
                        "sheet_name": sheet_name,
                        "row_range": f"Dòng {start_row + 1}-{end_row}",
                        "text": block_text
                    })

            total_blocks = max(1, len(sheet_blocks))
            for b_idx, block in enumerate(sheet_blocks, start=1):
                extracted_pages.append(
                    ExtractedPage(
                        doc_id=doc_id,
                        file_name=path.name,
                        page_number=b_idx,
                        total_pages=total_blocks,
                        text=block["text"],
                        location_label=f"Sheet '{block['sheet_name']}' ({block['row_range']})"
                    )
                )

        except Exception as e:
            raise RuntimeError(f"Error reading Excel file '{path.name}': {str(e)}") from e

        return extracted_pages


class MultiFormatDocumentLoader(BaseDocumentLoader):
    """
    Universal document loader supporting PDF (.pdf), Word (.docx), and Excel (.xlsx, .xls).
    """

    def __init__(self, min_char_threshold: int = 15):
        self.min_char_threshold = min_char_threshold
        self.pdf_loader = PDFDocumentLoader(min_char_threshold=min_char_threshold)
        self.docx_loader = DocxDocumentLoader(min_char_threshold=min_char_threshold)
        self.excel_loader = ExcelDocumentLoader(min_char_threshold=min_char_threshold)

    def load_document(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        """Dispatch document loading based on file extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found at: {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self.pdf_loader.load_single_pdf(path)
        elif suffix in [".docx", ".doc"]:
            return self.docx_loader.load_single_docx(path)
        elif suffix in [".xlsx", ".xls"]:
            return self.excel_loader.load_single_excel(path)
        else:
            raise ValueError(
                f"Định dạng file '{suffix}' chưa được hỗ trợ. "
                "Hệ thống hỗ trợ các định dạng: .pdf, .docx, .xlsx, .xls."
            )

    # Backward compatibility alias
    def load_single_pdf(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        return self.load_document(file_path)

    def load_multiple_documents(self, file_paths: List[Union[str, Path]]) -> List[ExtractedPage]:
        all_pages: List[ExtractedPage] = []
        for file_path in file_paths:
            all_pages.extend(self.load_document(file_path))
        return all_pages
