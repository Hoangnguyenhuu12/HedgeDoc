"""
Unit and Integration Tests for Hybrid OCR and Document Intelligence Engine.
Tests heading context tracking, table extraction to Markdown, context bleed cleanup,
hybrid digital/scanned routing, and unified Markdown normalization.
"""

import sys
from pathlib import Path
import pytest
import pymupdf as fitz

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_layer.ocr import (
    extract_headings,
    context_to_prompt,
    clean_context_bleed,
    merge_contexts,
    normalize_markdown_structure,
    table_to_markdown,
    extract_digital_page_markdown,
    metadata_to_yaml_frontmatter,
)
from data_layer.loader import PDFDocumentLoader, ExtractedPage


def test_heading_extraction_and_context_propagation():
    """Test extracting hierarchical headings and generating anti-hallucination prompt."""
    sample_text = (
        "# Chuyên đề 1: Phương pháp tọa độ trong không gian\n"
        "Đoạn mở đầu giới thiệu về hệ trục...\n\n"
        "## Bài 1. Tọa độ của vectơ\n"
        "Nội dung bài học...\n\n"
        "### Ví dụ 1\n"
        "Cho vectơ a = (1, 2, 3)...\n"
    )
    headings = extract_headings(sample_text)
    assert "# Chuyên đề 1" in headings
    assert "## Bài 1" in headings
    assert "### Ví dụ 1" in headings

    prompt_ctx = context_to_prompt(headings)
    assert "Book/Part: Chuyên đề 1" in prompt_ctx
    assert "Chapter/Lesson: Bài 1" in prompt_ctx
    assert "CRITICAL ANTI-HALLUCINATION RULES" in prompt_ctx

    # Test merging contexts across pages
    ctx_page1 = "# Chuyên đề 1 | ## Bài 1"
    ctx_page2 = "## Bài 2 | ### Ví dụ 1"
    merged = merge_contexts(ctx_page1, ctx_page2)
    assert "# Chuyên đề 1" in merged
    assert "## Bài 2" in merged
    assert "### Ví dụ 1" in merged


def test_clean_context_bleed():
    """Test removing breadcrumb leaks and trailing context echoes."""
    # 1. Breadcrumb line leak
    leaked_text = (
        "# Chuyên đề 1 | ## Bài 1 | ### Ví dụ 1\n"
        "Nội dung thật của trang tiếp theo ở đây.\n"
        "Dòng tiếp tục bình thường."
    )
    cleaned = clean_context_bleed(leaked_text, heading_context="# Chuyên đề 1 | ## Bài 1")
    assert "# Chuyên đề 1 | ## Bài 1" not in cleaned
    assert "Nội dung thật của trang tiếp theo" in cleaned

    # 2. Trailing echo leak at bottom of page
    trailing_leak = (
        "Nội dung bài tập trên trang.\n"
        "Tính giá trị của x và y.\n\n"
        "## Bài 1. Tọa độ của vectơ"
    )
    cleaned_trailing = clean_context_bleed(trailing_leak, heading_context="## Bài 1. Tọa độ của vectơ")
    assert "Tính giá trị của x và y." in cleaned_trailing
    assert not cleaned_trailing.strip().endswith("## Bài 1. Tọa độ của vectơ")


def test_markdown_structure_normalization():
    """Test unified Markdown normalization for digital and OCR output."""
    raw_input = (
        "chuyên đề 2 hình học phẳng\n"
        "bài 3. đường tròn\n"
        "Ví dụ 2\n"
        "Lời giải\n"
        "Cho đường tròn có phương trình $x^2 + y^2 = 25$."
    )
    norm = normalize_markdown_structure(raw_input)
    assert "# Chuyên đề 2" in norm
    assert "## Bài 3." in norm
    assert "### Ví dụ 2" in norm
    assert "#### Lời giải" in norm
    assert "$x^2 + y^2 = 25$" in norm


def test_metadata_yaml_frontmatter():
    """Test YAML frontmatter generation from metadata dict."""
    meta = {
        "title": "Chuyên đề Toán 10",
        "authors": ["Nguyễn Văn A", "Trần Thị B"],
        "publisher": "NXB Giáo Dục",
        "publish_at": "2023",
        "subject": "Toán",
        "grade_level": "10"
    }
    frontmatter = metadata_to_yaml_frontmatter(meta)
    assert frontmatter.startswith("---\n")
    assert frontmatter.endswith("---\n\n")
    assert "title: Chuyên đề Toán 10" in frontmatter
    assert "NXB Giáo Dục" in frontmatter


def test_digital_pdf_table_to_markdown(tmp_path):
    """Test that digital PDF tables are automatically converted to Markdown tables."""
    pdf_file = tmp_path / "test_table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # Insert text and table lines
    page.insert_text((50, 50), "# Financial Report Summary", fontsize=16)
    page.insert_text((50, 90), "Below is the detailed quarterly data:", fontsize=11)

    # Draw table grid
    rect = fitz.Rect(50, 120, 450, 220)
    page.draw_rect(rect, color=(0, 0, 0), width=1)
    # Horizontal line
    page.draw_line((50, 150), (450, 150), color=(0, 0, 0), width=1)
    # Vertical line
    page.draw_line((250, 120), (250, 220), color=(0, 0, 0), width=1)

    # Insert cells text
    page.insert_text((60, 140), "Category Item", fontsize=10)
    page.insert_text((260, 140), "Value (USD)", fontsize=10)
    page.insert_text((60, 180), "Q1 Revenue", fontsize=10)
    page.insert_text((260, 180), "500,000,000", fontsize=10)

    doc.save(pdf_file)
    doc.close()

    # Load with PDFDocumentLoader
    loader = PDFDocumentLoader(min_char_threshold=15, enable_ocr=False)
    pages = loader.load_single_pdf(pdf_file)

    assert len(pages) == 1
    page_text = pages[0].text
    assert "# Financial Report Summary" in page_text
    assert "| Category Item | Value (USD) |" in page_text
    assert "| --- | --- |" in page_text
    assert "| Q1 Revenue | 500,000,000 |" in page_text



def test_hybrid_fallback_on_sample_manual():
    """Test PDFDocumentLoader on HedgeDoc's sample manual PDF."""
    sample_pdf = BASE_DIR / "data" / "raw_docs" / "sample_manual.pdf"
    assert sample_pdf.exists(), "Sample manual PDF must exist"

    loader = PDFDocumentLoader(min_char_threshold=15, enable_ocr=False)
    pages = loader.load_single_pdf(sample_pdf)

    assert len(pages) > 0
    assert pages[0].doc_id is not None
    assert "HedgeDoc" in pages[0].text
    assert pages[0].page_number == 1


def test_live_vlm_ocr_scanned_page(tmp_path):
    """Test OCR on a purely rasterized scanned image page (0 native text characters)."""
    # 1. Create a page with text
    src_doc = fitz.open()
    src_page = src_doc.new_page(width=500, height=300)
    src_page.insert_text((50, 100), "HedgeDoc Multimodal OCR Test Page", fontsize=18)
    src_page.insert_text((50, 150), "Day la noi dung kiem thu OCR tu dong bang VLM.", fontsize=14)

    # 2. Rasterize the page to PNG image (pure pixels, no text layer)
    pix = src_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_bytes = pix.tobytes("png")
    src_doc.close()

    # 3. Create a new PDF and embed only this image
    scanned_pdf = tmp_path / "scanned_doc.pdf"
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=500, height=300)
    new_page.insert_image(new_page.rect, stream=img_bytes)
    new_doc.save(scanned_pdf)
    new_doc.close()

    # Verify that native text layer is completely empty
    check_doc = fitz.open(scanned_pdf)
    assert len(check_doc[0].get_text("text").strip()) == 0
    check_doc.close()

    # 4. Run PDFDocumentLoader with enable_ocr=True!
    loader = PDFDocumentLoader(min_char_threshold=15, enable_ocr=True)
    pages = loader.load_single_pdf(scanned_pdf)

    assert len(pages) == 1
    assert "(OCR)" in pages[0].location_label
    assert "HedgeDoc" in pages[0].text or "OCR" in pages[0].text

