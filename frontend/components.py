"""
Reusable UI Components.
Renders citation cards, document sidebars, and custom minimalist CSS.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st

__all__ = [
    "inject_custom_css",
    "render_header",
    "render_claude_thinking_box",
    "render_thought_and_citations",
    "render_citation_cards",
    "render_document_sidebar_cards",
    "render_copy_button",
    "get_suggested_questions",
    "render_suggested_prompts",
    "render_model_selector"
]

CSS_PATH = Path(__file__).parent / "styles.css"


def inject_custom_css() -> None:
    """Inject custom minimalist CSS styles for Streamlit."""
    if CSS_PATH.exists():
        css_content = CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)



def render_header(scope_label: str = "All documents") -> None:
    """Render minimal header."""
    st.markdown(
        """
        <div class="app-header">
            <div class="app-title">HedgeDoc</div>
            <div class="app-subtitle">Document analysis and retrieval system with precise page-level citations.</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_claude_thinking_box(thought_markdown: str, expanded: bool = False) -> None:
    """
    Render minimal thinking drawer, collapsed by default.
    """
    if not thought_markdown:
        return

    with st.expander("Thinking", expanded=expanded):
        st.markdown(thought_markdown)


def render_thought_and_citations(
    thinking_steps: Optional[List[Dict[str, str]]] = None,
    citations: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Backward compatibility helper."""
    render_citation_cards(citations or [])


def render_citation_cards(citations: List[Dict[str, Any]]) -> None:
    """
    Render citation cards in a clean, vertical list inside a collapsed expander.
    """
    if not citations:
        return

    with st.expander(f"Sources & Citations ({len(citations)})", expanded=False):
        for cit in citations:
            file_name = cit.get("file_name", "Document")
            loc_label = cit.get("location_label") or f"Trang {cit.get('page_number', 'N/A')}"
            rerank_score = cit.get("rerank_score")
            distance = cit.get("distance")

            score_parts = []
            if rerank_score is not None:
                score_parts.append(f"Độ khớp: {rerank_score * 100:.0f}%")
            elif distance is not None:
                score_parts.append(f"Dist: {distance:.4f}")
            score_str = f" • *{', '.join(score_parts)}*" if score_parts else ""

            snippet = cit.get("snippet", "").strip()

            st.markdown(f"**{file_name} - {loc_label}**{score_str}")
            if snippet:
                st.markdown(f'<div class="citation-snippet">"{snippet}"</div>', unsafe_allow_html=True)
            st.markdown("")


@st.dialog("Xác nhận xóa tài liệu", width="small")
def _show_delete_dialog(doc_id: str, file_name: str, on_delete: Optional[Any] = None) -> None:
    """Modal confirmation dialog for removing a document from index."""
    st.write(f"Bạn có chắc muốn xóa tài liệu **{file_name}** khỏi kho dữ liệu?")
    apply_all = st.checkbox(
        "Áp dụng cho các file sau (không hỏi lại)",
        value=False,
        key=f"chk_apply_all_{doc_id}"
    )

    col_del, col_can = st.columns(2, gap="small")
    with col_del:
        if st.button("Delete", key=f"dlg_btn_del_{doc_id}", type="primary", use_container_width=True):
            if apply_all:
                st.session_state["skip_delete_confirm"] = True
            if on_delete:
                on_delete(doc_id, file_name)
            st.rerun()
    with col_can:
        if st.button("Cancel", key=f"dlg_btn_can_{doc_id}", use_container_width=True):
            st.rerun()


def render_document_sidebar_cards(
    docs: List[Dict[str, Any]],
    on_delete: Optional[Any] = None
) -> None:
    """Render list of indexed documents in the sidebar with vertical alignment and popup confirmation."""
    if not docs:
        st.caption("No documents indexed yet.")
        return

    for doc in docs:
        doc_id = doc.get("doc_id", "")
        file_name = doc.get("file_name", "Unknown")

        col_info, col_del = st.columns([0.84, 0.16], gap="small", vertical_alignment="center")
        with col_info:
            st.markdown(
                f"""
                <div class="sidebar-doc-card">
                    <div class="sidebar-doc-title" title="{file_name}">{file_name}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_del:
            if st.button("✕", key=f"btn_del_{doc_id}", help=f"Remove '{file_name}' from index", type="tertiary"):
                if st.session_state.get("skip_delete_confirm", False):
                    if on_delete:
                        on_delete(doc_id, file_name)
                    st.rerun()
                else:
                    _show_delete_dialog(doc_id, file_name, on_delete)


def render_copy_button(text: str, key_suffix: str = "") -> None:
    """Disabled copy button to prevent browser rendering artifacts."""
    return


DEFAULT_SUGGESTED_QUESTIONS: List[str] = [
    "Tóm tắt các chủ đề cốt lõi trong kho tài liệu hiện tại",
    "So sánh các điểm khác biệt chính giữa các tài liệu đã nạp",
    "Tài liệu nào chứa nội dung liên quan đến quy trình hoặc hướng dẫn?"
]

TOPIC_SUGGESTIONS: Dict[tuple, List[str]] = {
    ("hoang-tu-be", "hoang tu be", "little prince"): [
        "Ý nghĩa cuộc gặp gỡ giữa Hoàng tử bé và con cáo là gì?",
        "Tác phẩm gửi gắm thông điệp gì về tình bạn, tình yêu và trách nhiệm?",
        "Tóm tắt chuyến hành trình của Hoàng tử bé qua các tiểu hành tinh"
    ],
    ("tony", "ca phe"): [
        "Những lời khuyên cốt lõi của Dượng Tony về tinh thần tự lập và thái độ sống?",
        "Tác giả chia sẻ quan điểm gì về việc học ngoại ngữ và văn hóa đi làm?",
        "Tóm tắt những câu chuyện truyền cảm hứng nổi bật trong cuốn sách"
    ],
    ("manual", "guide", "huong dan"): [
        "Tài liệu này bao gồm những quy trình hướng dẫn cụ thể nào?",
        "Các bước thực hiện chuẩn được mô tả như thế nào?",
        "Những lưu ý an toàn và cảnh báo quan trọng nhất cần tuân thủ?"
    ],
    ("report", "bao cao", "finance"): [
        "Tóm tắt các kết quả và chỉ số quan trọng nhất trong báo cáo",
        "Những rủi ro và thách thức chính được đề cập là gì?",
        "Các đề xuất và định hướng tiếp theo trong tài liệu?"
    ]
}


def get_suggested_questions(selected_scope_label: Optional[str] = None) -> List[str]:
    """Generate context-aware starter questions tailored to the active document."""
    if not selected_scope_label or selected_scope_label.startswith("All documents"):
        return DEFAULT_SUGGESTED_QUESTIONS

    clean_name = selected_scope_label.split(" (")[0]
    name_lower = clean_name.lower()

    for keywords, questions in TOPIC_SUGGESTIONS.items():
        if any(kw in name_lower for kw in keywords):
            return questions

    stem = clean_name.rsplit(".", 1)[0]
    return [
        f"Tóm tắt ngắn gọn các luận điểm chính trong {stem}",
        f"Những nội dung và khái niệm quan trọng nhất cần nắm được?",
        f"Tài liệu này đưa ra các phân tích hoặc giải pháp cụ thể nào?"
    ]


def render_suggested_prompts(prompts: List[str]) -> Optional[str]:
    """Render clean, minimal starter prompt chips in a horizontal column layout."""
    if not prompts:
        return None

    st.markdown(
        """
        <div class="prompts-container">
            <div class="prompts-label">Suggested Questions</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    cols = st.columns(len(prompts), gap="small")
    clicked_prompt = None
    for idx, prompt in enumerate(prompts):
        with cols[idx]:
            if st.button(prompt, key=f"chip_{idx}", use_container_width=True, type="secondary"):
                clicked_prompt = prompt
    return clicked_prompt


def render_model_selector() -> tuple[str, str]:
    """
    Render a clean model & provider selector in the sidebar.
    Allows user to switch between Cloud (Gemini, OpenAI) and Local (Ollama).
    Returns (provider, model_name).
    """
    from backend.providers.factory import ProviderFactory
    from backend.providers.ollama_provider import check_ollama_status

    provider_options = ["Gemini (Cloud)", "OpenAI (Cloud)", "Ollama (Local)"]
    provider_map = {
        "Gemini (Cloud)": "gemini",
        "OpenAI (Cloud)": "openai",
        "Ollama (Local)": "ollama"
    }
    reverse_provider_map = {v: k for k, v in provider_map.items()}

    # Initialize session state for model selection if not present
    if "selected_provider" not in st.session_state:
        st.session_state["selected_provider"] = "gemini"

    current_provider_display = reverse_provider_map.get(
        st.session_state["selected_provider"], "Gemini (Cloud)"
    )
    current_idx = provider_options.index(current_provider_display) if current_provider_display in provider_options else 0

    selected_display = st.selectbox(
        "Nhà cung cấp (Provider)",
        options=provider_options,
        index=current_idx,
        help="Chọn giữa mô hình Đám mây (Gemini/OpenAI) hoặc Mô hình cục bộ (Ollama Local)"
    )
    selected_provider = provider_map[selected_display]
    st.session_state["selected_provider"] = selected_provider

    # Model choices based on selected provider
    if selected_provider == "gemini":
        available_models = ProviderFactory.get_available_models("gemini")
        default_model = "gemini-2.5-flash"
        idx = available_models.index(default_model) if default_model in available_models else 0
        selected_model = st.selectbox("Mô hình (Model)", options=available_models, index=idx)
        st.caption("Khuyên dùng `gemini-2.5-flash`: Miễn phí 1,500 lượt/ngày, tốc độ cao.")

    elif selected_provider == "openai":
        available_models = ProviderFactory.get_available_models("openai")
        default_model = "gpt-4o-mini"
        idx = available_models.index(default_model) if default_model in available_models else 0
        selected_model = st.selectbox("Mô hình (Model)", options=available_models, index=idx)
        st.caption("Sử dụng OpenAI API Key từ cấu hình `.env`.")

    else:  # ollama
        ollama_status = check_ollama_status(timeout=0.6)
        if ollama_status["online"]:
            st.caption("Ollama: Đang hoạt động (Online)")
            installed = ollama_status["models"]
            if installed:
                model_options = installed + ["(Nhập model khác...)"]
                chosen_opt = st.selectbox("Mô hình Local", options=model_options)
                if chosen_opt == "(Nhập model khác...)":
                    selected_model = st.text_input("Tên model Ollama", value="qwen2.5:7b").strip()
                else:
                    selected_model = chosen_opt
            else:
                selected_model = st.text_input("Tên model Ollama", value="qwen2.5:7b").strip()
                st.caption("Chưa có model nào được tải. Chạy `ollama pull qwen2.5:7b` trong terminal.")
        else:
            st.caption("Ollama: Chưa kết nối (Offline)")
            st.info("Vui lòng mở ứng dụng Ollama hoặc chạy lệnh `ollama serve` trong PowerShell.")
            selected_model = st.text_input("Tên model Ollama", value="qwen2.5:7b").strip()

    st.session_state["selected_model"] = selected_model
    return selected_provider, selected_model



