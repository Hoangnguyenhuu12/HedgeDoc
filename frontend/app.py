"""
Main Streamlit Application for HedgeDoc Modular Document AI.
Integrates:
- Document Quality Gate (OCR Readiness Assessment)
- Document OCR Engine (Structured Layout, Blocks, Tables)
- Document RAG Engine (Hybrid Retrieval, Parent-Child Chunking, Multi-Provider LLM)
"""

from pathlib import Path
import sys
import streamlit as st

# Configure sys.path so HedgeDoc package is directly importable
CURRENT_FILE = Path(__file__).resolve()
HEDGEDOC_ROOT = CURRENT_FILE.parent.parent
WORKSPACE_ROOT = HEDGEDOC_ROOT.parent

for p in [str(WORKSPACE_ROOT), str(HEDGEDOC_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from HedgeDoc.configs.app_config import config
from HedgeDoc.workflows.document_pipeline import DocumentPipelineOrchestrator
from HedgeDoc.frontend.components import (
    inject_custom_css,
    render_header,
    render_quality_gate_card,
    render_ocr_inspection,
    render_thinking_box,
    render_citations,
    render_suggested_prompts
)

# Page configuration
st.set_page_config(
    page_title="HedgeDoc — Nền tảng Trí tuệ Tài liệu",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()
config.reload()

# Initialize session state
if "orchestrator" not in st.session_state or not hasattr(st.session_state.orchestrator, "delete_document"):
    st.session_state.orchestrator = DocumentPipelineOrchestrator()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_assessment" not in st.session_state:
    st.session_state.latest_assessment = None

if "latest_ocr" not in st.session_state:
    st.session_state.latest_ocr = None

orchestrator: DocumentPipelineOrchestrator = st.session_state.orchestrator

# ==============================================================================
# SIDEBAR: DOCUMENT INGESTION & QUALITY PIPELINE
# ==============================================================================
with st.sidebar:
    st.subheader("Tài liệu & Kiểm định")
    st.caption("Quản lý tài liệu theo kiến trúc đa tầng độc lập.")

    uploaded_files = st.file_uploader(
        "Tải lên tài liệu mới",
        type=["pdf", "docx", "xlsx", "xls", "png", "jpg"],
        accept_multiple_files=True,
        help="Hệ thống sẽ chạy qua Cổng kiểm soát chất lượng trước khi nhận dạng OCR và lập chỉ mục RAG."
    )

    if uploaded_files:
        if st.button("Nạp vào kho tri thức", type="primary", use_container_width=True):
            progress_bar = st.progress(0, text="Bắt đầu quy trình nạp...")
            for idx, up_file in enumerate(uploaded_files, start=1):
                save_path = config.RAW_DOCS_DIR / up_file.name
                with open(save_path, "wb") as f:
                    f.write(up_file.getbuffer())

                def on_progress(msg: str, pct: float):
                    progress_bar.progress(pct, text=f"[{idx}/{len(uploaded_files)}] {up_file.name}: {msg}")

                result = orchestrator.process_document(save_path, progress_callback=on_progress)

                if result.get("status") == "success":
                    st.session_state.latest_assessment = (up_file.name, result.get("quality_assessment"))
                    st.session_state.latest_ocr = result.get("ocr_summary")
                    st.success(f"Nạp thành công: {up_file.name}")
                    st.toast(f"Đã nạp thành công: {up_file.name}")
                elif result.get("status") == "rejected":
                    st.session_state.latest_assessment = (up_file.name, result.get("quality_assessment"))
                    st.error(f"Từ chối {up_file.name}: {result.get('message')}")
                else:
                    st.error(f"Lỗi nạp {up_file.name}: {result.get('message')}")

            progress_bar.progress(1.0, text="Hoàn tất quy trình xử lý.")

    # Show Quality Gate scorecard if available
    if st.session_state.latest_assessment:
        with st.expander("Kết quả kiểm định chất lượng", expanded=True):
            fname, assess = st.session_state.latest_assessment
            render_quality_gate_card(assess, file_name=fname)
            if st.session_state.latest_ocr:
                render_ocr_inspection(st.session_state.latest_ocr)

    # Show persistent knowledge base inventory (persists across F5 reloads!)
    with st.expander("Kho tri thức đã lưu", expanded=True):
        indexed_docs = orchestrator.list_indexed_documents()
        if indexed_docs:
            for idx, d in enumerate(indexed_docs):
                row_col1, row_col2 = st.columns([0.82, 0.18])
                with row_col1:
                    st.markdown(
                        f"<div style='font-size: 13px; line-height: 1.4; padding-top: 4px; word-break: break-all;'>"
                        f"<b>{d['file_name']}</b><br/>"
                        f"<span style='color: #94a3b8; font-size: 11px;'>{d['chunk_count']} đoạn véc-tơ</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with row_col2:
                    if st.button("✕", key=f"del_btn_{idx}", help=f"Xóa {d['file_name']}"):
                        st.session_state.pending_delete = d["file_name"]

            # Warning confirmation dialog
            if st.session_state.get("pending_delete"):
                target = st.session_state.pending_delete
                st.warning(f"Xác nhận xóa tài liệu: **{target}**?")
                c1, c2 = st.columns(2)
                if c1.button("Xóa", type="primary", use_container_width=True, key="conf_del"):
                    orchestrator.delete_document(target)
                    st.session_state.pending_delete = None
                    st.toast(f"Đã xóa tài liệu: {target}")
                    st.rerun()
                if c2.button("Hủy", use_container_width=True, key="cancel_del"):
                    st.session_state.pending_delete = None
                    st.rerun()
        else:
            st.caption("Chưa có tài liệu nào trong kho tri thức.")

    st.markdown("---")

    # Configuration panel
    with st.expander("Cấu hình mô hình & Tham số", expanded=False):
        top_k = st.slider("Số lượng đoạn trích xuất (Top-K)", min_value=1, max_value=8, value=config.TOP_K_RETRIEVAL)
        st.caption(f"Mô hình ngôn ngữ: `{config.LLM_PROVIDER}` / `{config.LLM_MODEL}`")
        st.caption(f"Mô hình nhúng: `{config.EMBEDDING_PROVIDER}` / `{config.EMBEDDING_MODEL}`")
        if st.button("Làm mới cấu hình", use_container_width=True):
            config.reload()
            st.toast("Đã nạp lại các biến môi trường.")
            st.rerun()

    if st.session_state.messages:
        if st.button("Xóa lịch sử hội thoại", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# ==============================================================================
# MAIN VIEW: CHAT & DOCUMENT INTELLIGENCE
# ==============================================================================
render_header()

def handle_user_query(prompt_text: str):
    """Appends query and triggers generation."""
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("thought"):
            render_thinking_box(msg["thought"])
        if msg.get("citations"):
            render_citations(msg["citations"])

# Handle pending assistant response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_prompt = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        with st.spinner("Đang định tuyến và trích xuất căn cứ tài liệu..."):
            res = orchestrator.stream_query(
                query_text=user_prompt,
                top_k=top_k,
                chat_history=history
            )

        thought = res.get("thought", "")
        citations = res.get("citations", [])
        stream_gen = res.get("stream")

        if thought:
            render_thinking_box(thought)

        if stream_gen:
            def safe_stream():
                try:
                    for token in stream_gen:
                        yield token
                except Exception as exc:
                    yield f"\n\n*(Thông báo: Quá trình truyền token bị gián đoạn: {str(exc)})*"

            answer = st.write_stream(safe_stream())
        else:
            answer = res.get("answer", "Không tìm thấy nội dung liên quan trong tài liệu.")
            st.markdown(answer)

        if citations:
            render_citations(citations)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "thought": thought,
            "citations": citations
        })
        st.rerun()

# Show suggested prompts ONLY when conversation is empty
if not st.session_state.messages:
    render_suggested_prompts(handle_user_query)

# Chat input box
user_input = st.chat_input("Nhập câu hỏi tra cứu tài liệu tại đây...")
if user_input:
    handle_user_query(user_input)
