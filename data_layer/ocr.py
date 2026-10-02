"""
Hybrid OCR and Markdown Document Intelligence Engine for HedgeDoc.
Integrates PyMuPDF digital text & table extraction with Vision-Language Model (VLM) OCR.
Applies heading context tracking across pages, anti-hallucination controls, and unified Markdown normalization.
"""

import base64
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

import pymupdf as fitz
import requests
import yaml

from config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heading context tracking & Anti-Hallucination
# ---------------------------------------------------------------------------

def extract_headings(text: str) -> str:
    """
    Extract the most recent heading for each level (#..####).
    Returns formatted string: '# Chuyên đề 1 | ## Bài 1. Tiêu đề | ### Ví dụ 3'
    """
    headings = re.findall(r'^(#{1,4}\s+.+)$', text, re.MULTILINE)
    if not headings:
        return ""
    last_per_level: Dict[int, str] = {}
    for h in headings:
        level = len(h) - len(h.lstrip('#'))
        last_per_level[level] = h.strip()
    return " | ".join(last_per_level[k] for k in sorted(last_per_level))


def context_to_prompt(heading_context: str) -> str:
    """
    Convert heading context to plain-text system instructions (NOT Markdown templates).
    Prevents the Vision model from copying or echoing Markdown headings unnecessarily.
    """
    if not heading_context:
        return ""

    level_label = {
        1: "Book/Part",
        2: "Chapter/Lesson",
        3: "Section",
        4: "Sub-block",
    }

    lines = ["Document Context (Hierarchy):", "You are currently inside:"]
    for part in heading_context.split(" | "):
        part = part.strip()
        if not part.startswith("#"):
            continue
        level = len(part) - len(part.lstrip('#'))
        title = part.lstrip('#').strip()
        label = level_label.get(level, "Section")
        suffix = " (content continues onto this page)" if level >= 3 else ""
        lines.append(f"  {label}: {title}{suffix}")

    lines += [
        "",
        "CRITICAL ANTI-HALLUCINATION RULES:",
        "  - DO NOT output the context headings above unless they are physically printed on this page image.",
        "  - DO NOT close sections by echoing context headings at the end of the page.",
        "  - If the page starts with continuation text, extract it directly without inventing a title.",
        "  - If a new heading is visibly printed in the image, format it properly using Markdown (#, ##, ###).",
    ]
    return "\n".join(lines)


def clean_context_bleed(text: str, heading_context: str = "") -> str:
    """
    Remove context bleed artifacts:
    1. Single-line breadcrumbs like '# Chuyên đề 1 | ## Bài 2'
    2. Trailing echo headings at the bottom of the page that match previous context.
    """
    lines = text.split("\n")
    cleaned: List[str] = []

    # Clean single-line breadcrumb leaks
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and re.search(r'\s*[|>]\s*#{1,6}\s', stripped):
            continue
        cleaned.append(line)

    # Clean trailing echo headings
    if heading_context:
        context_titles: set = set()
        for part in heading_context.split(" | "):
            part = part.strip()
            if part.startswith("#"):
                context_titles.add(part.lower())
                context_titles.add(part.lstrip('#').strip().lower())

        while cleaned:
            last = cleaned[-1].strip()
            if not last:
                cleaned.pop()
            elif last.lower() in context_titles:
                cleaned.pop()
            elif last.startswith("#"):
                last_title = last.lstrip('#').strip().lower()
                if last_title in context_titles:
                    cleaned.pop()
                else:
                    break
            else:
                break

    return "\n".join(cleaned)


def merge_contexts(ctx_a: str, ctx_b: str) -> str:
    """
    Merge two heading contexts, giving precedence to new headings from ctx_b.
    """
    if not ctx_a:
        return ctx_b
    if not ctx_b:
        return ctx_a

    def parse(ctx: str) -> Dict[int, str]:
        res = {}
        for part in ctx.split(" | "):
            part = part.strip()
            if part.startswith("#"):
                lvl = len(part) - len(part.lstrip('#'))
                res[lvl] = part
        return res

    merged = parse(ctx_a)
    merged.update(parse(ctx_b))
    return " | ".join(merged[k] for k in sorted(merged))


# ---------------------------------------------------------------------------
# Unified Markdown Normalization (Applies to both Digital & OCR extracted text)
# ---------------------------------------------------------------------------

CHUYEN_DE_PATTERN = re.compile(r'^(?:#+\s*)?(Chuyên đề\s+\d+.*)', re.IGNORECASE)
BAI_PATTERN = re.compile(r'^(?:#+\s*)?(Bài\s+\d+.*)', re.IGNORECASE)
PHAN_BAI_TAP_PATTERN = re.compile(r'^\s*(?:#+\s*)?(?:\*\*\s*)?(BÀI\s+TẬP)(?:\s*\*\*)?\s*$', re.IGNORECASE)
VD_BT_PATTERN = re.compile(r'^(?:#+\s*)?(?:\*\*\s*)?(Ví dụ|Bài tập)\s*(\d+.*)?(?:\s*\*\*)?', re.IGNORECASE)
GIAI_PATTERN = re.compile(r'^(?:#+\s*)?(?:\*\*\s*)?(Giải|Lời giải)\s*(:?)(?:\s*\*\*)?\s*$', re.IGNORECASE)
NUMBERED_SEC_PATTERN = re.compile(r'^\s*(?:#+\s*)?(?:\*\*)?\s*(\d+|[IVX]+)\s*\.\s*(?:\*\*)?\s+([^\.\n]+?)(?:\s*\*\*)?\s*$')

def normalize_markdown_structure(text: str) -> str:
    """
    Standardize document headings, exercise blocks, solution blocks, and clean artifacts.
    Ensures that digital PyMuPDF extraction and VLM OCR extraction share the identical Markdown schema.
    """
    if not text:
        return ""

    # Clean redundant whitespace & carriage returns
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove image links or imgur links if any
    text = re.sub(r'!\[.*?\]\(https?://\S+\)', '', text)

    lines = text.split("\n")
    normalized_lines: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            normalized_lines.append("")
            i += 1
            continue

        # Ignore standalone page markers
        if re.match(r'^\[PAGE\s*\d+\]$', stripped, re.IGNORECASE):
            i += 1
            continue

        # Standardize 'Chuyên đề X'
        m_cd = CHUYEN_DE_PATTERN.match(stripped)
        if m_cd:
            cd_title = re.sub(r'^(?:#+\s*)?chuy[eê]n\s+[dđ][eề]\b', 'Chuyên đề', m_cd.group(1).strip(), flags=re.IGNORECASE)
            normalized_lines.append(f"# {cd_title}")
            i += 1
            continue

        # Standardize 'Bài X'
        m_bai = BAI_PATTERN.match(stripped)
        if m_bai:
            bai_title = re.sub(r'^(?:#+\s*)?b[aà]i\b', 'Bài', m_bai.group(1).strip(), flags=re.IGNORECASE)
            normalized_lines.append(f"## {bai_title}")
            i += 1
            continue


        # Standardize 'BÀI TẬP'
        if PHAN_BAI_TAP_PATTERN.match(stripped):
            normalized_lines.append("### BÀI TẬP")
            i += 1
            continue

        # Standardize 'Ví dụ X'
        m_vd = VD_BT_PATTERN.match(stripped)
        if m_vd:
            label = m_vd.group(1).strip()
            suffix = m_vd.group(2).strip() if m_vd.group(2) else ""
            normalized_lines.append(f"### {label} {suffix}".strip())
            i += 1
            continue

        # Standardize 'Lời giải / Giải'
        if GIAI_PATTERN.match(stripped):
            normalized_lines.append("#### Lời giải")
            i += 1
            continue

        # Standardize numbered sections like '1. Khái niệm'
        m_sec = NUMBERED_SEC_PATTERN.match(stripped)
        if m_sec and not re.search(r'[\^=]', stripped):
            num = m_sec.group(1).strip()
            title = m_sec.group(2).replace('**', '').strip()
            # Only consider as heading if title is reasonably short (< 90 chars)
            if len(title) <= 90 and not title.endswith('.'):
                normalized_lines.append(f"### {num}. {title}")
                i += 1
                continue

        normalized_lines.append(line)
        i += 1

    result = "\n".join(normalized_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


# ---------------------------------------------------------------------------
# Digital Table Extraction & Formatting using PyMuPDF
# ---------------------------------------------------------------------------

def table_to_markdown(table) -> str:
    """
    Convert a PyMuPDF Table object into a clean GitHub Flavored Markdown table.
    """
    try:
        rows = table.extract()
        if not rows or len(rows) < 1:
            return ""

        def clean_cell(cell: Any) -> str:
            if cell is None:
                return ""
            c_str = str(cell).replace("\r", " ").replace("\n", " ")
            c_str = re.sub(r"\s+", " ", c_str)
            return c_str.replace("|", "\\|").strip()

        headers = [clean_cell(c) for c in rows[0]]
        # If all headers are empty, create default col headers
        if not any(headers):
            headers = [f"Col {idx+1}" for idx in range(len(headers))]

        col_count = len(headers)
        md_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * col_count) + " |"
        ]

        for row in rows[1:]:
            cells = [clean_cell(c) for c in row]
            # Pad row if missing columns
            while len(cells) < col_count:
                cells.append("")
            md_lines.append("| " + " | ".join(cells[:col_count]) + " |")

        return "\n".join(md_lines)
    except Exception as e:
        logger.warning(f"Error converting table to markdown: {e}")
        return ""


def extract_digital_page_markdown(page: fitz.Page) -> str:
    """
    Extract text from a digital PDF page, detecting and preserving tables in Markdown syntax.
    """
    try:
        tabs = page.find_tables()
        tables_list = tabs.tables if hasattr(tabs, "tables") else []
    except Exception:
        tables_list = []

    if not tables_list:
        raw_text = page.get_text("text")
        return normalize_markdown_structure(raw_text)

    # For pages with tables, extract text blocks and inject markdown tables at appropriate locations
    table_bboxes = [tab.bbox for tab in tables_list]
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

    content_parts: List[str] = []
    inserted_tables = set()

    for block in blocks:
        bx0, by0, bx1, by1, btext, bno, btype = block
        block_rect = fitz.Rect(bx0, by0, bx1, by1)

        # Check if this block falls inside any table bbox
        is_inside_table = False
        for t_idx, t_bbox in enumerate(table_bboxes):
            t_rect = fitz.Rect(t_bbox)
            if t_rect.intersects(block_rect):
                is_inside_table = True
                if t_idx not in inserted_tables:
                    md_table = table_to_markdown(tables_list[t_idx])
                    if md_table:
                        content_parts.append("\n\n" + md_table + "\n\n")
                    inserted_tables.add(t_idx)
                break

        if not is_inside_table and btext.strip():
            content_parts.append(btext.strip())

    # Ensure any tables that were not caught by block intersections are appended
    for t_idx, tab in enumerate(tables_list):
        if t_idx not in inserted_tables:
            md_table = table_to_markdown(tab)
            if md_table:
                content_parts.append("\n\n" + md_table + "\n\n")

    full_page_text = "\n\n".join(content_parts)
    return normalize_markdown_structure(full_page_text)


# ---------------------------------------------------------------------------
# Vision-Language Model OCR Client
# ---------------------------------------------------------------------------

HEADING_RULES = (
    "Extract visibly present text from this image into Markdown format.\n"
    "STRICT RULES:\n"
    "1. NO HALLUCINATION: Do not invent, describe, summarize, or output image URLs/alt text.\n"
    "2. OUTPUT only the extracted text in Markdown. Format tables cleanly using Markdown syntax (| Header |).\n"
    "3. Format formulas cleanly using LaTeX ($...$ or $$...$$).\n"
    "4. HEADINGS:\n"
    "   - Major section/part -> # [TITLE]\n"
    "   - 'Chuyên đề ...' -> # Chuyên đề X. [TITLE]\n"
    "   - 'Bài ...'       -> ## Bài X. [TITLE]\n"
    "   - Numbered items  -> ### [Number]. [TITLE]\n"
    "   - 'Ví dụ ...'     -> ### Ví dụ X\n"
    "   - 'Lời giải'      -> #### Lời giải\n"
    "5. Do NOT end output with a trailing context heading. If the page ends mid-sentence, stop there.\n"
)


def rasterize_page_to_base64(page: fitz.Page, dpi_scale: float = 2.0) -> str:
    """
    Render a PDF page to base64-encoded PNG image.
    """
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi_scale, dpi_scale))
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def ocr_page_vlm(
    page: fitz.Page,
    page_idx: int,
    base_url: str,
    model: str,
    heading_context: str = "",
    timeout: int = 120
) -> Tuple[int, str]:
    """
    OCR a single PDF page using an OpenAI-compatible Vision-Language Model API.
    """
    try:
        b64_img = rasterize_page_to_base64(page, dpi_scale=1.7)

        system_content = (
            "You are an OCR assistant that converts document images into structured Markdown.\n"
            "Preserve exact Vietnamese text, tables, and mathematical formulas."
        )
        if heading_context:
            system_content += f"\n\n{context_to_prompt(heading_context)}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
                        {"type": "text", "text": HEADING_RULES},
                    ],
                },
            ],
            "max_tokens": 4096,
            "temperature": 0.0,
        }

        url = f"{base_url.rstrip('/')}/chat/completions"
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 404 and "/v1" in base_url:
            fallback_url = base_url.replace("/v1", "").rstrip('/') + "/chat/completions"
            resp = requests.post(fallback_url, json=payload, timeout=timeout)

        resp.raise_for_status()
        raw_text = resp.json()["choices"][0]["message"]["content"]
        # Strip code fences if model wrapped entire output in ```markdown
        raw_text = re.sub(r"^```(?:markdown)?\s*\n", "", raw_text)
        raw_text = re.sub(r"\n```\s*$", "", raw_text)

        cleaned_text = clean_context_bleed(raw_text, heading_context)
        normalized = normalize_markdown_structure(cleaned_text)
        return page_idx, normalized
    except Exception as e:
        logger.warning(f"OCR failed for page {page_idx + 1}: {e}")
        # Graceful fallback: return whatever raw text fitz can extract
        return page_idx, normalize_markdown_structure(page.get_text("text"))


# ---------------------------------------------------------------------------
# Metadata Extraction from Cover & Copyright Pages
# ---------------------------------------------------------------------------

METADATA_PROMPT = """\
You are analyzing scanned cover and copyright pages from a Vietnamese textbook or publication.
Extract document metadata as a strict JSON object with the following fields:
{
  "title": "Full title of the document or book",
  "authors": ["Author 1", "Author 2"],
  "publisher": "Publisher name",
  "publish_at": "Publication year (e.g. 2022 or 2024)",
  "subject": "Subject or field (e.g. Toán, Vật lí, Hóa học, Tin học, Pháp luật, etc.)",
  "grade_level": "Grade level or audience (e.g. 10, 11, 12 if applicable)",
  "isbn": "ISBN code if present"
}
Return ONLY the raw JSON object, without explanations or Markdown fences.
"""


def extract_document_metadata_vlm(
    pdf_path: Path,
    base_url: str,
    model: str,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Extract structured metadata (Authors, Publisher, Year, Subject) from cover & copyright pages.
    """
    try:
        with fitz.open(pdf_path) as doc:
            n_pages = len(doc)
            if n_pages < 2:
                return {}

            cover_indices = [0]
            if n_pages > 2:
                cover_indices.append(1)

            # Copyright page is usually penultimate or last
            copy_indices = [max(0, n_pages - 2), max(0, n_pages - 1)]
            target_indices = sorted(list(set(cover_indices + copy_indices)))

            content: List[Dict[str, Any]] = []
            for idx in target_indices:
                if idx < n_pages:
                    b64 = rasterize_page_to_base64(doc[idx], dpi_scale=1.5)
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}
                    })

            content.append({"type": "text", "text": METADATA_PROMPT})

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a metadata extractor. Return JSON only."},
                    {"role": "user", "content": content}
                ],
                "max_tokens": 1024,
                "temperature": 0.0
            }

            url = f"{base_url.rstrip('/')}/chat/completions"
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code == 404 and "/v1" in base_url:
                url = base_url.replace("/v1", "").rstrip('/') + "/chat/completions"
                resp = requests.post(url, json=payload, timeout=timeout)

            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw).strip()
            meta = json.loads(raw)
            if isinstance(meta, dict):
                return meta
    except Exception as e:
        logger.warning(f"Could not extract document metadata via VLM: {e}")
    return {}


def metadata_to_yaml_frontmatter(meta: Dict[str, Any]) -> str:
    """
    Convert document metadata dict into a standardized YAML Frontmatter block.
    """
    if not meta:
        return ""
    clean_meta = {k: v for k, v in meta.items() if v}
    if not clean_meta:
        return ""
    yaml_str = yaml.safe_dump(clean_meta, allow_unicode=True, default_flow_style=False)
    return f"---\n{yaml_str}---\n\n"


# ---------------------------------------------------------------------------
# Hybrid Document Pipeline Orchestrator
# ---------------------------------------------------------------------------

def process_pdf_pages_hybrid(
    file_path: Path,
    doc_id: str,
    min_char_threshold: int = 15,
    enable_ocr: bool = True,
    base_url: str = "",
    model: str = "",
    window_size: int = 3,
    extract_metadata: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
):
    """
    Hybrid PDF Processor:
    - Digital extraction (PyMuPDF) with table-to-markdown conversion for text-rich pages.
    - Sliding window VLM OCR with heading context tracking for scanned / low-text pages (< min_char_threshold).
    - Preserves heading context continuously across both digital and scanned pages.
    - Uniform Markdown normalization for identical structure regardless of extraction source.
    - Automatic cover/copyright metadata extraction.
    """
    from .loader import ExtractedPage

    base_url = base_url or config.OCR_BASE_URL
    model = model or config.OCR_MODEL
    window_size = window_size or config.OCR_WINDOW_SIZE

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Optional metadata extraction from cover/copyright pages
    frontmatter = ""
    if extract_metadata and config.OCR_EXTRACT_METADATA and enable_ocr:
        if progress_callback:
            progress_callback(0, 100, f"Đang trích xuất metadata bìa/bản quyền cho '{file_path.name}'...")
        meta = extract_document_metadata_vlm(file_path, base_url, model)
        frontmatter = metadata_to_yaml_frontmatter(meta)

    doc = fitz.open(file_path)
    n_pages = len(doc)
    if n_pages == 0:
        doc.close()
        return []

    # Assess pages: digital vs scanned
    page_types: List[Tuple[int, bool, str]] = []
    for idx in range(n_pages):
        raw = doc[idx].get_text("text").strip()
        is_digital = len(raw) >= min_char_threshold
        page_types.append((idx, is_digital, raw))

    results: Dict[int, Tuple[str, bool]] = {}
    heading_context = ""
    i = 0

    while i < n_pages:
        idx, is_digital, raw_text = page_types[i]

        if is_digital:
            # 1. Digital text page: Extract text and tables to Markdown
            text = extract_digital_page_markdown(doc[idx])
            results[idx] = (text, False)

            # Update heading context from digital text so following scanned pages inherit it
            new_ctx = extract_headings(text)
            if new_ctx:
                heading_context = merge_contexts(heading_context, new_ctx)

            if progress_callback:
                progress_callback(i + 1, n_pages, f"Trích xuất văn bản số trang {i + 1}/{n_pages}")
            i += 1

        else:
            # 2. Scanned / image-only page: Requires VLM OCR
            if not enable_ocr:
                # Fallback when OCR is disabled
                text = normalize_markdown_structure(raw_text)
                if text:
                    results[idx] = (text, False)
                i += 1
            else:
                # Group consecutive scanned pages into sliding window (window_size)
                window_indices: List[int] = []
                while i < n_pages and not page_types[i][1] and len(window_indices) < window_size:
                    window_indices.append(i)
                    i += 1

                start_p, end_p = window_indices[0] + 1, window_indices[-1] + 1
                if progress_callback:
                    progress_callback(
                        window_indices[0] + 1,
                        n_pages,
                        f"Đang chạy OCR VLM trang {start_p}-{end_p}/{n_pages}..."
                    )

                window_results: Dict[int, str] = {}
                if len(window_indices) == 1:
                    p_idx = window_indices[0]
                    _, ocr_txt = ocr_page_vlm(doc[p_idx], p_idx, base_url, model, heading_context)
                    window_results[p_idx] = ocr_txt
                else:
                    with ThreadPoolExecutor(max_workers=len(window_indices)) as executor:
                        futures = {
                            executor.submit(ocr_page_vlm, doc[p_idx], p_idx, base_url, model, heading_context): p_idx
                            for p_idx in window_indices
                        }
                        for future in as_completed(futures):
                            p_idx, ocr_txt = future.result()
                            window_results[p_idx] = ocr_txt

                # Record results and propagate headings sequentially
                for p_idx in window_indices:
                    txt = window_results.get(p_idx, "")
                    results[p_idx] = (txt, True)
                    new_ctx = extract_headings(txt)
                    if new_ctx:
                        heading_context = merge_contexts(heading_context, new_ctx)

    doc.close()

    # Assemble ExtractedPage objects
    extracted_pages: List[ExtractedPage] = []
    for idx in range(n_pages):
        if idx not in results:
            continue
        text, is_ocr = results[idx]
        if not text.strip():
            continue

        # Attach YAML frontmatter to the very first page with content
        if len(extracted_pages) == 0 and frontmatter:
            text = frontmatter + text

        tag = " (OCR)" if is_ocr else ""
        page_text = f"# Tài liệu: {file_path.name} (Trang {idx + 1}{tag})\n\n{text}"

        extracted_pages.append(
            ExtractedPage(
                doc_id=doc_id,
                file_name=file_path.name,
                page_number=idx + 1,
                total_pages=n_pages,
                text=page_text,
                location_label=f"Trang {idx + 1}{tag}"
            )
        )

    return extracted_pages

