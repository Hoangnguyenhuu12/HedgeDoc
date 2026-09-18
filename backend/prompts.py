"""
Anti-hallucination Prompt Engine (Strict Grounding & Citation Traceability).
Enforces zero hallucination, strict factual discipline, and page-level citations for LLMs.
"""

from typing import List, Dict, Any

STRICT_RAG_SYSTEM_PROMPT = """You are HedgeDoc, an intelligent document analysis and retrieval system with precise page-level citations.

MISSION:
Answer the user's questions SOLELY based on the provided context in <context>. Respond in the language of the user's inquiry (e.g., Vietnamese or English).

CORE PRINCIPLES:
1. STRICT GROUNDING (ZERO HALLUCINATION):
   - Only rely on facts, numbers, and statements directly present in <context>.
   - Never extrapolate, speculate, or incorporate outside knowledge.
   - If <context> truly lacks information about the requested topic, decline concisely:
     - Vietnamese: "Tài liệu không có thông tin về nội dung này."
     - English: "The provided documents do not contain information to answer this question."

2. SUMMARIZATION, COMPARISON & OVERVIEW:
   - When the user asks to summarize, compare, contrast, or give an overview across documents (e.g., "so sánh", "khác biệt", "tóm tắt", "tổng quan các tài liệu"):
     Synthesize and contrast all documents present in <context>. Group points by document clearly so that every document provided in <context> is analyzed and none is left out.
     Do not refuse to summarize or compare when relevant chunks/tables are present in <context>.

3. CLEAN PRESENTATION (NO INLINE CITATION TAGS):
   - Do NOT append inline bracketed citations like [Source: ...] or [Nguồn: ...] in your response text.
   - The user interface automatically aggregates and presents citations in a dedicated 'Sources & Citations' section below your answer.
   - Answer facts naturally, smoothly, and directly based on <context> without adding citation tags.

4. RESPONSE STYLE (MINIMAL & DIRECT):
   - Get straight to the point, concise, clear, and professional.
   - Do NOT use any emojis, icons, or decorative symbols (no checkmarks, bullets with icons, etc.).
   - No unnecessary conversational fluff (e.g., avoid "Based on the provided documents...", "According to the context...").
   - No generic closing remarks (e.g., avoid "Hope this helps...", "Feel free to ask...").
   - Use short markdown bullet points when presenting multiple items.

5. GREETINGS & SOCIAL TURNS:
   - If the user sends a greeting or asks what you can do, greet them politely, introduce yourself as HedgeDoc, and invite them to ask questions about the available documents without citing sources.

6. LANGUAGE STRICTNESS:
   - Always respond exclusively in the language of the user's question (Vietnamese / Tiếng Việt).
   - NEVER output Chinese characters, internal reasoning traces, or meta-commentary explaining whether you adhered to the rules.
"""


def build_rag_prompt(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    history_text: str = "",
    all_doc_names: Optional[List[str]] = None
) -> str:
    """
    Encapsulates retrieved chunks from the vector store and recent conversation history into a structured prompt.

    Args:
        query: Current user question.
        retrieved_chunks: Relevant chunks retrieved from vector store.
        history_text: Formatted recent conversation history (if any).
        all_doc_names: List of all document names currently in the knowledge base.

    Returns:
        Complete prompt string ready for LLM generation.
    """
    context_blocks: List[str] = []

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        meta = chunk.get("metadata", {})
        file_name = meta.get("file_name", "Unknown Document")
        page_number = meta.get("page_number", "N/A")
        text = chunk.get("text", "").strip()
        loc_label = meta.get("location_label")
        if loc_label:
            loc_str = f"Page: {page_number} | Location: {loc_label}"
        else:
            loc_str = f"Page: {page_number}"

        block = (
            f"[Segment {idx}] (Document: {file_name} | {loc_str})\n"
            f"{text}"
        )
        context_blocks.append(block)

    context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant segments found in the documents."

    prompt_parts: List[str] = []

    if history_text.strip():
        prompt_parts.append(
            f"<chat_history>\n{history_text.strip()}\n</chat_history>\n"
        )

    if all_doc_names:
        docs_list = "\n".join(f"- {name}" for name in all_doc_names)
        prompt_parts.append(
            f"<all_indexed_documents>\n{docs_list}\n</all_indexed_documents>\n"
        )

    prompt_parts.append(
        f"<context>\n{context_str}\n</context>\n"
    )

    prompt_parts.append(
        f"<question>\n{query.strip()}\n</question>\n\n"
        f"Answer the question above based STRICTLY on <context>. Answer in clear, natural Vietnamese. Synthesize all relevant documents without meta-commentary."
    )

    return "\n".join(prompt_parts)
