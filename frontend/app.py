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
    render_suggested_prompts,
    render_interactive_chips
)
from HedgeDoc.agents.language_utils import detect_language, clean_doc_title

# Page configuration
st.set_page_config(
    page_title="HedgeDoc — Nền tảng Trí tuệ Tài liệu",
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
else:
    # Auto-sanitize any lingering messages from previous session states
    for m in st.session_state.messages:
        if "Lễ tân" in m.get("content", "") or "lễ tân" in m.get("content", ""):
            m["content"] = (
                "Tôi là **HedgeDoc** — Nền tảng Trí tuệ và Khai phá Tri thức Tài liệu.\n\n"
                "**Khả năng chính:**\n\n"
                "- **Kiểm định chất lượng**: Đo lường độ nét, tương phản, độ phân giải tài liệu trước khi bóc tách.\n"
                "- **Bóc tách OCR**: Trích xuất chính xác văn bản số, bảng biểu và cấu trúc dữ liệu.\n"
                "- **Tra cứu thông minh**: Phân đoạn, lập chỉ mục véc-tơ và trả lời câu hỏi trực tiếp từ tài liệu đã nạp."
            )
        if "Lễ tân" in m.get("thought", "") or "lễ tân" in m.get("thought", ""):
            m["thought"] = (
                "[Bộ điều phối]: Nhận diện câu hỏi thông tin chung / hướng dẫn hệ thống.\n"
                "-> Phản hồi trực tiếp, súc tích về tính năng và tài liệu hiện có trong kho."
            )

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
                row_col1, row_col2 = st.columns([0.84, 0.16])
                clean_t = clean_doc_title(d["file_name"])
                ext = Path(d["file_name"]).suffix.lower()
                with row_col1:
                    st.markdown(
                        f"<div style='font-size: 13px; line-height: 1.4; padding-top: 2px; word-break: break-word;'>"
                        f"<b>{clean_t}</b><span style='color: #71717a; font-size: 12px; font-weight: normal;'>{ext}</span><br/>"
                        f"<span style='color: #a1a1aa; font-size: 11px;'>{d['chunk_count']} đoạn véc-tơ</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with row_col2:
                    st.markdown('<span class="del-btn-anchor"></span>', unsafe_allow_html=True)
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

from HedgeDoc.agents.language_utils import detect_language

def handle_user_query(prompt_text: str):
    """Appends query and triggers generation."""
    st.session_state.messages.append({
        "role": "user",
        "content": prompt_text,
        "lang": detect_language(prompt_text)
    })
    st.rerun()

# Display chat history
for msg_idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        msg_lang = msg.get("lang") or detect_language(msg.get("content", ""))
        if msg.get("thought"):
            render_thinking_box(msg["thought"], lang=msg_lang)
        if msg.get("citations"):
            render_citations(msg["citations"], lang=msg_lang)
        if msg.get("suggested_followups") and msg_idx == len(st.session_state.messages) - 1:
            render_interactive_chips(
                msg["suggested_followups"],
                handle_user_query,
                key_prefix=f"hist_sug_{msg_idx}",
                lang=msg_lang
            )

# Handle pending assistant response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_prompt = st.session_state.messages[-1]["content"]
    query_lang = detect_language(user_prompt)
    with st.chat_message("assistant"):
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        spinner_text = "Routing and retrieving grounded citations..." if query_lang == "en" else "Đang định tuyến và trích xuất căn cứ tài liệu..."
        with st.spinner(spinner_text):
            res = orchestrator.stream_query(
                query_text=user_prompt,
                top_k=top_k,
                chat_history=history
            )

        thought = res.get("thought", "")
        citations = res.get("citations", [])
        stream_gen = res.get("stream")
        suggested_followups = res.get("suggested_followups", [])

        if thought:
            render_thinking_box(thought, lang=query_lang)

        if stream_gen:
            def safe_stream():
                try:
                    for token in stream_gen:
                        yield token
                except Exception as exc:
                    err_msg = f"\n\n*(Notice: Token streaming interrupted: {str(exc)})*" if query_lang == "en" else f"\n\n*(Thông báo: Quá trình truyền token bị gián đoạn: {str(exc)})*"
                    yield err_msg

            answer = st.write_stream(safe_stream())
        else:
            default_not_found = "No relevant content found in the documents." if query_lang == "en" else "Không tìm thấy nội dung liên quan trong tài liệu."
            answer = res.get("answer", default_not_found)
            st.markdown(answer)

        if citations:
            render_citations(citations, lang=query_lang)

        if suggested_followups:
            render_interactive_chips(
                suggested_followups,
                handle_user_query,
                key_prefix="live_sug",
                lang=query_lang
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "thought": thought,
            "citations": citations,
            "suggested_followups": suggested_followups,
            "lang": query_lang
        })
        st.rerun()

# Show suggested prompts ONLY when conversation is empty
if not st.session_state.messages:
    general_prompts = [
        "Tóm tắt nội dung tài liệu",
        "Tra cứu quy định & điều khoản chính",
        "Kiểm định chất lượng tài liệu scan"
    ]
    render_interactive_chips(general_prompts, handle_user_query, key_prefix="init_sug", lang="vi")

# Chat input box
user_input = st.chat_input("Nhập câu hỏi tra cứu tài liệu / Ask a question...")
if user_input:
    handle_user_query(user_input)
