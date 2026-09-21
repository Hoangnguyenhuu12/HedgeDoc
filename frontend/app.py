"""
Main HedgeDoc Streamlit Application.
Connects RAGEngine with user interface, supporting real-time streaming, multi-file management, and page-level citations.
"""

from pathlib import Path
import sys
import streamlit as st

# Add workspace root to sys.path for safe absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import importlib
import data_layer.loader
import data_layer.vector_store
import backend.providers.ollama_provider
import backend.providers.factory
import backend.prompts
import backend.rag_engine
import frontend.components
importlib.reload(data_layer.loader)
importlib.reload(data_layer.vector_store)
importlib.reload(backend.providers.ollama_provider)
importlib.reload(backend.providers.factory)
importlib.reload(backend.prompts)
importlib.reload(backend.rag_engine)
importlib.reload(frontend.components)

from config import config
from backend.rag_engine import RAGEngine, strip_inline_citations
from backend.memory import ConversationMemoryBuffer
from frontend.components import (
    inject_custom_css,
    render_header,
    render_claude_thinking_box,
    render_citation_cards,
    render_thought_and_citations,
    render_document_sidebar_cards,
    render_copy_button,
    get_suggested_questions,
    render_suggested_prompts,
    render_model_selector
)

# Page configuration
st.set_page_config(
    page_title="HedgeDoc",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()

# Auto hot-reload .env configuration on each session cycle
config.reload()

# Manage conversation memory in session state, re-instantiate RAGEngine fresh on each run
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemoryBuffer()

engine = RAGEngine(memory=st.session_state.memory)

# Initialize message history
if "messages" not in st.session_state:
    st.session_state.messages = []


# ==============================================================================
# SIDEBAR: DOCUMENT MANAGEMENT & CONFIGURATION
# ==============================================================================
with st.sidebar:
    st.title("Documents")
    st.caption("Quản lý tài liệu PDF trong kho tri thức.")

    # Retrieve current indexed documents
    indexed_docs = engine.vector_store.get_indexed_documents_summary()
    indexed_filenames = {doc["file_name"] for doc in indexed_docs}

    # 1. Upload new documents (PDF, Word, Excel)
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "docx", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Hỗ trợ PDF, Word (.docx), Excel (.xlsx, .xls). Hệ thống tự động trích xuất nội dung và lập chỉ mục vào ChromaDB."
    )

    if uploaded_files:
        if len(uploaded_files) > 5:
            st.warning("⚠️ Khuyến nghị: Nên tải 3–5 tài liệu mỗi lượt để hệ thống xử lý nhanh và ổn định nhất.")

        new_files = [f for f in uploaded_files if f.name not in indexed_filenames]
        is_processing = st.session_state.get("is_processing_docs", False)

        if new_files:
            # Only show process button when there are new files
            btn_label = "Đang xử lý tài liệu..." if is_processing else f"Nạp {len(new_files)} tài liệu mới"
            if st.button(btn_label, disabled=is_processing, use_container_width=True, type="primary"):
                st.session_state["is_processing_docs"] = True
                st.session_state["upload_status"] = None
                st.rerun()
        else:
            # Single concise message when all files are already indexed, no disabled buttons
            if not st.session_state.get("upload_status"):
                st.caption("Tất cả tài liệu tải lên đã được lưu trong kho.")

    # Process documents pipeline when triggered
    if st.session_state.get("is_processing_docs", False) and uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in indexed_filenames]
        files_to_process = new_files if new_files else uploaded_files

        progress_bar = st.progress(0, text="Bắt đầu nạp sách...")
        total_count = len(files_to_process)
        errors = []
        success_count = 0
        total_pages_added = 0
        total_chunks_added = 0

        try:
            for idx, uploaded_file in enumerate(files_to_process, start=1):
                save_path = config.RAW_DOCS_DIR / uploaded_file.name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                def file_progress_cb(current, total, msg):
                    pct = current / total if total > 0 else 1.0
                    overall = (idx - 1) / total_count + (pct / total_count)
                    progress_bar.progress(
                        min(1.0, max(0.0, overall)),
                        text=f"[{idx}/{total_count}] {uploaded_file.name}: {msg}"
                    )

                res = engine.index_document(
                    save_path,
                    force_reindex=False,
                    progress_callback=file_progress_cb
                )

                if res.get("status") in ["success", "already_indexed"]:
                    success_count += 1
                    total_pages_added += res.get("total_pages", 0)
                    total_chunks_added += res.get("chunk_count", 0)
                elif res.get("status") == "error":
                    errors.append(f"{uploaded_file.name}: {res.get('message', 'Lỗi')}")

            progress_bar.progress(1.0, text="Hoàn tất xử lý tài liệu.")
            if errors:
                st.session_state["upload_status"] = {
                    "type": "error",
                    "message": "Có lỗi khi nạp: " + "; ".join(errors)
                }
                st.toast("Có lỗi khi nạp tài liệu.")
            else:
                st.session_state["upload_status"] = {
                    "type": "success",
                    "message": f"Đã nạp thành công {success_count} tài liệu ({total_pages_added} trang, {total_chunks_added} đoạn)."
                }
                st.toast(f"Đã nạp thành công {success_count} tài liệu.")
        except Exception as exc:
            st.session_state["upload_status"] = {
                "type": "error",
                "message": f"Lỗi hệ thống: {str(exc)}"
            }
            st.toast(f"Lỗi nạp sách: {str(exc)}")
        finally:
            st.session_state["is_processing_docs"] = False
            st.rerun()

    # Single notification display (only 1 clean alert, no extra headings or dismiss buttons)
    if st.session_state.get("upload_status"):
        status_info = st.session_state["upload_status"]
        if status_info["type"] == "success":
            st.success(status_info["message"])
        else:
            st.error(status_info["message"])

    st.markdown("---")

    # 2. List of indexed documents
    st.subheader("Tài liệu đã lưu")

    def on_delete_document(doc_id: str, file_name: str) -> None:
        if engine.delete_document(doc_id, file_name):
            st.session_state["upload_status"] = None
            st.toast(f"Đã xóa '{file_name}' khỏi kho dữ liệu.")
        else:
            st.error(f"Không thể xóa '{file_name}'.")

    render_document_sidebar_cards(indexed_docs, on_delete=on_delete_document)

    st.markdown("---")

    # 3. Streamlined configuration & Model selection
    top_k = config.TOP_K_RETRIEVAL
    selected_provider = config.LLM_PROVIDER
    selected_model = config.LLM_MODEL

    with st.expander("Mô hình & Cấu hình", expanded=True):
        selected_provider, selected_model = render_model_selector()
        st.markdown("---")
        top_k = st.slider("Số đoạn trích xuất (Top-K)", min_value=1, max_value=8, value=config.TOP_K_RETRIEVAL)
        st.caption(f"Embedding: `{config.EMBEDDING_PROVIDER}` (`{config.EMBEDDING_MODEL}`)")
        if st.button("🔄 Nạp lại cấu hình .env", use_container_width=True, help="Tải lại các giá trị mới nhất từ file .env mà không cần restart server"):
            config.reload()
            st.toast("Đã nạp lại cấu hình từ .env!")
            st.rerun()

    # Only show Clear Chat History button when there are messages
    if st.session_state.messages:
        if st.button("Xóa lịch sử chat", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            if "memory" in st.session_state:
                st.session_state.memory.clear()
            st.rerun()


# ==============================================================================
# MAIN WORKSPACE: RAG CONVERSATION
# ==============================================================================
render_header()

# Render all persisted session messages
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg.get("thought_process"):
            render_claude_thinking_box(msg["thought_process"], expanded=False)
        st.write(strip_inline_citations(msg["content"]))
        if msg.get("citations"):
            render_citation_cards(msg["citations"])
        if msg.get("role") == "assistant" and msg.get("model_name"):
            st.caption(f"Mô hình: `{msg['model_name']}`")

# If conversation is empty, display contextual starter prompt suggestions
if not st.session_state.messages:
    prompts = get_suggested_questions("All documents")
    clicked_chip = render_suggested_prompts(prompts)
    if clicked_chip:
        st.session_state["pending_prompt"] = clicked_chip
        st.rerun()

# Handle new user query (from chat input or clicked starter chip)
user_question = st.chat_input("Ask a question about the documents...")
active_question = user_question or st.session_state.pop("pending_prompt", None)

if active_question:
    # 1. Display user query
    st.session_state.messages.append({"role": "user", "content": active_question})
    with st.chat_message("user"):
        st.write(active_question)

    # 2. Process response from HedgeDoc RAG Engine
    with st.chat_message("assistant"):
        try:
            with st.spinner("Processing..."):
                query_res = engine.query(
                    question=active_question,
                    top_k=top_k,
                    doc_id_filter=None,
                    stream=True,
                    llm_provider=selected_provider,
                    llm_model=selected_model
                )
                thought_process = query_res.get("thought_process", "")
                citations = query_res.get("citations", [])

            # Single thinking drawer, collapsed by default
            if thought_process:
                render_claude_thinking_box(thought_process, expanded=False)

            # Stream generated answer
            full_answer = st.write_stream(query_res["answer_stream"])

            # Render citations if present
            if citations:
                render_citation_cards(citations)

            active_model_name = query_res.get("model_name", selected_model)
            st.caption(f"Mô hình: `{active_model_name}`")

            # Persist to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_answer,
                "thought_process": thought_process,
                "citations": citations,
                "model_name": active_model_name
            })
        except Exception as query_exc:
            error_msg = f"Đã xảy ra lỗi khi xử lý câu hỏi: {str(query_exc)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "thought_process": "",
                "citations": []
            })
