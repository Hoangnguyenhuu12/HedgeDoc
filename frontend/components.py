"""
UI Components for the HedgeDoc Streamlit Application.
Provides rendering functions for:
- Quality Gate Scorecards & OCR Readiness Badges
- OCR Inspection & Table Extraction Summaries
- Thinking / Reasoning Process Box
- Page-level Citation Cards
- Model Selectors & Header Elements
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
STYLE_PATH = CURRENT_DIR / "styles.css"


def inject_custom_css():
    """Injects styles.css into the Streamlit app."""
    if STYLE_PATH.exists():
        with open(STYLE_PATH, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_header():
    """Renders clean minimalist header."""
    st.markdown("### HedgeDoc — Khai thác Tri thức Tài liệu")
    st.caption("Kiểm định chất lượng, trích xuất cấu trúc và tra cứu tri thức.")
    st.markdown("---")


def render_quality_gate_card(assessment: Dict[str, Any], file_name: str = ""):
    """
    Renders visual scorecard for Document Quality Gate assessment.
    """
    score = assessment.get("overall_quality", 0.0)
    rec = assessment.get("recommendation", "direct_to_ocr")
    issues = assessment.get("issues_summary", []) or assessment.get("detected_issues", [])

    if rec == "direct_to_ocr":
        badge_class = "badge-direct"
        badge_text = "Đủ tiêu chuẩn — Nhận dạng trực tiếp"
    elif rec == "enhance_before_ocr":
        badge_class = "badge-enhance"
        badge_text = "Cảnh báo — Cần tiền xử lý tăng cường"
    else:
        badge_class = "badge-reject"
        badge_text = "Từ chối — Chất lượng không đạt"

    st.markdown(
        f"""
        <div class="quality-card">
            <div class="quality-header">
                <span class="quality-title">Kiểm định chất lượng: <b>{file_name}</b></span>
                <span class="quality-score-badge {badge_class}">{badge_text}</span>
            </div>
            <div style="font-size: 13px; margin-bottom: 8px;">
                Điểm sẵn sàng nhận dạng: <b>{score:.1f} / 5.0</b>
            </div>
        """,
        unsafe_allow_html=True
    )

    # Breakdown metrics from first page if present
    pages = assessment.get("page_assessments", []) or assessment.get("pages_assessment", [])
    if pages:
        first_metrics = pages[0].get("metrics", {})
        blur_val = first_metrics.get("blur_score", 0.0)
        contrast_val = first_metrics.get("contrast_score", 0.0)
        dpi_val = first_metrics.get("estimated_dpi", 0.0) or first_metrics.get("dpi_estimate", 0.0)
        shadow_val = first_metrics.get("shadow_disparity", 0.0) or first_metrics.get("shadow_score", 0.0)

        st.markdown(
            f"""
            <div class="metric-grid">
                <div class="metric-pill">
                    <span class="metric-pill-label">Độ sắc nét</span>
                    <span class="metric-pill-val">{blur_val:.1f}</span>
                </div>
                <div class="metric-pill">
                    <span class="metric-pill-label">Độ tương phản</span>
                    <span class="metric-pill-val">{contrast_val:.1f}</span>
                </div>
                <div class="metric-pill">
                    <span class="metric-pill-label">Độ phân giải ước tính</span>
                    <span class="metric-pill-val">{int(dpi_val)} DPI</span>
                </div>
                <div class="metric-pill">
                    <span class="metric-pill-label">Chênh lệch bóng đổ</span>
                    <span class="metric-pill-val">{shadow_val:.1f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if issues and (rec != "direct_to_ocr" or score < 4.5):
        trans = {
            "low_contrast": "độ tương phản hơi thấp",
            "low_resolution": "độ phân giải thấp",
            "mild_blur": "mờ nhẹ",
            "severe_blur": "mờ nghiêm trọng",
            "harsh_shadow": "bóng đổ gắt"
        }
        translated_issues = [trans.get(i, i) for i in issues]
        issues_str = ", ".join(translated_issues)
        color = "#f87171" if rec == "reject" else "#fbbf24"
        st.markdown(
            f"<div style='margin-top: 10px; font-size: 12px; color: {color};'>"
            f"<b>Lưu ý chất lượng:</b> {issues_str}</div>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_ocr_inspection(ocr_summary: Dict[str, Any]):
    """Renders structured summary of extracted OCR data."""
    if not ocr_summary:
        return

    pages = ocr_summary.get("total_pages", 0)
    blocks = ocr_summary.get("total_blocks", 0)
    tables = ocr_summary.get("total_tables", 0)
    chars = ocr_summary.get("char_count", 0)
    backend = ocr_summary.get("backend_used", "digital_native")

    st.markdown(
        f"""
        <div class="ocr-card">
            <div class="ocr-header">
                <span>Kết quả trích xuất văn bản</span>
                <span class="ocr-badge-tag">{backend}</span>
            </div>
            <div class="ocr-stats-grid">
                <div class="ocr-stat-item">
                    <span class="ocr-stat-label">Số trang</span>
                    <span class="ocr-stat-value">{pages}</span>
                </div>
                <div class="ocr-stat-item">
                    <span class="ocr-stat-label">Khối nội dung</span>
                    <span class="ocr-stat-value">{blocks}</span>
                </div>
                <div class="ocr-stat-item">
                    <span class="ocr-stat-label">Bảng biểu</span>
                    <span class="ocr-stat-value">{tables}</span>
                </div>
                <div class="ocr-stat-item">
                    <span class="ocr-stat-label">Tổng ký tự</span>
                    <span class="ocr-stat-value">{chars:,}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_thinking_box(thought: str):
    """Renders Claude-style thinking block."""
    if not thought or not thought.strip():
        return
    with st.expander("Quy trình suy luận và tra cứu", expanded=False):
        st.markdown(f"<div class='thought-box'>{thought}</div>", unsafe_allow_html=True)


def render_citations(citations: List[Dict[str, Any]]):
    """Renders page-level citations."""
    if not citations:
        return
    with st.expander(f"Nguồn tài liệu trích dẫn ({len(citations)})", expanded=False):
        for idx, cit in enumerate(citations, start=1):
            source = cit.get("source", "Tài liệu")
            page = cit.get("page", 1)
            score = cit.get("score", 0.0)
            text = cit.get("text", "")
            st.markdown(
                f"""
                <div class="citation-card">
                    <div class="citation-header">[{idx}] {source} (Trang {page}) — Độ tương đồng: {score:.2f}</div>
                    <div class="citation-snippet">{text}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_suggested_prompts(on_click_callback):
    """Renders prompt suggestion chips."""
    prompts = [
        "Tóm tắt các điểm chính của tài liệu này",
        "Có những quy định hoặc điều kiện gì đáng chú ý?",
        "Trích xuất các bảng biểu hoặc dữ liệu định lượng quan trọng"
    ]
    cols = st.columns(len(prompts))
    for idx, p in enumerate(prompts):
        if cols[idx].button(p, key=f"sug_{idx}", use_container_width=True):
            on_click_callback(p)
