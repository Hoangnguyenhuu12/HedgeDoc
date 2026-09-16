"""
Reusable UI Components.
Renders citation cards, document sidebars, and custom minimalist CSS.
"""

from typing import List, Dict, Any, Optional
import streamlit as st

__all__ = [
    "inject_custom_css",
    "render_header",
    "render_claude_thinking_box",
    "render_thought_and_citations",
    "render_citation_cards",
    "render_document_sidebar_cards"
]


def inject_custom_css() -> None:
    """Inject custom minimalist CSS styles for Streamlit."""
    st.markdown(
        """
        <style>
        /* General typography and spacing */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Header bar */
        .app-header {
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        }
        .app-title {
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0;
        }
        .app-subtitle {
            font-size: 0.95rem;
            color: #6c757d;
            margin-top: 0.25rem;
        }

        /* Citation Badge */
        .citation-container {
            margin-top: 0.8rem;
            padding-top: 0.5rem;
            border-top: 1px dashed rgba(128, 128, 128, 0.25);
        }
        .citation-badge {
            display: inline-block;
            padding: 0.2rem 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 4px;
            background-color: rgba(66, 133, 244, 0.12);
            color: #1a73e8;
            margin-right: 0.4rem;
            margin-bottom: 0.4rem;
            border: 1px solid rgba(66, 133, 244, 0.25);
        }
        .citation-snippet {
            font-size: 0.85rem;
            line-height: 1.5;
            color: #495057;
            background: rgba(0, 0, 0, 0.02);
            padding: 0.6rem 0.8rem;
            border-radius: 6px;
            border-left: 3px solid #1a73e8;
            margin-top: 0.3rem;
            font-style: italic;
        }

        /* Sidebar Styling */
        .sidebar-doc-card {
            padding: 0.6rem;
            margin-bottom: 0.5rem;
            background: rgba(128, 128, 128, 0.05);
            border-radius: 6px;
            border: 1px solid rgba(128, 128, 128, 0.15);
        }
        .sidebar-doc-title {
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.2rem;
            word-break: break-word;
        }
        .sidebar-doc-meta {
            font-size: 0.75rem;
            color: #6c757d;
        }

        /* Minimal Expander */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(128, 128, 128, 0.15) !important;
            border-radius: 6px !important;
            background: transparent !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stExpander"] details summary p {
            font-size: 0.82rem !important;
            color: #8a8f98 !important;
            font-weight: 500 !important;
        }
        div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
            font-size: 0.85rem !important;
            color: #a1a1aa !important;
            line-height: 1.6 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_header() -> None:
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
            page_num = cit.get("page_number", "N/A")
            distance = cit.get("distance")
            dist_str = f" (Distance: {distance:.4f})" if distance is not None else ""
            snippet = cit.get("snippet", "").strip()

            st.markdown(f"**{file_name} - Page {page_num}**{dist_str}")
            if snippet:
                st.markdown(f'<div class="citation-snippet">"{snippet}"</div>', unsafe_allow_html=True)
            st.markdown("")


def render_document_sidebar_cards(docs: List[Dict[str, Any]]) -> None:
    """Render list of indexed documents in the sidebar."""
    if not docs:
        st.caption("No documents indexed yet.")
        return

    for doc in docs:
        file_name = doc.get("file_name", "Unknown")
        pages = doc.get("total_pages", 0)
        chunks = doc.get("chunk_count", 0)

        st.markdown(
            f"""
            <div class="sidebar-doc-card">
                <div class="sidebar-doc-title">{file_name}</div>
                <div class="sidebar-doc-meta">{pages} pages | {chunks} chunks</div>
            </div>
            """,
            unsafe_allow_html=True
        )
