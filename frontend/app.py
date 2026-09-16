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
import backend.rag_engine
import frontend.components
importlib.reload(backend.rag_engine)
importlib.reload(frontend.components)

from config import config
from backend.rag_engine import RAGEngine
from backend.memory import ConversationMemoryBuffer
from frontend.components import (
    inject_custom_css,
    render_header,
    render_claude_thinking_box,
    render_citation_cards,
    render_thought_and_citations,
    render_document_sidebar_cards
)

# Page configuration
st.set_page_config(
    page_title="HedgeDoc",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()

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
    st.caption("Manage PDF documents in the knowledge base.")

    # 1. Upload new PDF files
    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="The system automatically extracts text, chunks content, and stores embeddings in ChromaDB."
    )

    if uploaded_files:
        if st.button("Index Uploaded Files", use_container_width=True):
            for uploaded_file in uploaded_files:
                save_path = config.RAW_DOCS_DIR / uploaded_file.name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with st.spinner(f"Processing: {uploaded_file.name}..."):
                    res = engine.index_document(save_path, force_reindex=False)
                    if res.get("status") == "success":
                        st.success(f"Successfully indexed {res.get('chunk_count', 0)} chunks from '{uploaded_file.name}'")
                    else:
                        st.info(res.get("message", "Processed."))
            st.rerun()

    st.markdown("---")

    # 2. Scope Filter
    indexed_docs = engine.vector_store.get_indexed_documents_summary()
    doc_options = {"All documents": None}
    for doc in indexed_docs:
        doc_options[f"{doc['file_name']} ({doc['total_pages']} pages)"] = doc["doc_id"]

    selected_scope_label = st.selectbox(
        "Search Scope",
        options=list(doc_options.keys()),
        index=0,
        help="Restrict questions to a specific document or search across all indexed files."
    )
    selected_doc_id = doc_options[selected_scope_label]

    st.markdown("---")

    # 3. List of indexed documents
    st.subheader("Indexed Documents")
    render_document_sidebar_cards(indexed_docs)

    st.markdown("---")

    # 4. Quick parameter configuration
    st.subheader("Configuration")
    top_k = st.slider("Retrieved Chunks (Top-K)", min_value=1, max_value=8, value=config.TOP_K_RETRIEVAL)

    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        if "memory" in st.session_state:
            st.session_state.memory.clear()
        st.rerun()

    st.caption(f"LLM: `{config.LLM_MODEL}` | Embedding: `{config.EMBEDDING_MODEL}`")


# ==============================================================================
# MAIN WORKSPACE: RAG CONVERSATION
# ==============================================================================
render_header()

# Render all persisted session messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("thought_process"):
            render_claude_thinking_box(msg["thought_process"], expanded=False)
        st.write(msg["content"])
        if msg.get("citations"):
            render_citation_cards(msg["citations"])

# Handle new user query
if user_question := st.chat_input("Ask a question about the documents..."):
    # 1. Display user query
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.write(user_question)

    # 2. Process response from HedgeDoc RAG Engine
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            query_res = engine.query(
                question=user_question,
                top_k=top_k,
                doc_id_filter=selected_doc_id,
                stream=True
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

        # Persist to session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_answer,
            "thought_process": thought_process,
            "citations": citations
        })
