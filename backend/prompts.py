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
   - If <context> lacks the answer, decline concisely:
     - Vietnamese: "Tài liệu không có thông tin về nội dung này."
     - English: "The provided documents do not contain information to answer this question."

2. SOURCE CITATIONS:
   - Attach citations immediately after each factual claim using the format: [Source: <file_name> - Page <page_number>] (or [Nguồn: <file_name> - Trang <page_number>] in Vietnamese).

3. RESPONSE STYLE (MINIMAL & DIRECT):
   - Get straight to the point, concise, clear, and professional.
   - Do NOT use any emojis, icons, or decorative symbols (no checkmarks, bullets with icons, etc.).
   - No unnecessary conversational fluff (e.g., avoid "Based on the provided documents...", "According to the context...").
   - No generic closing remarks (e.g., avoid "Hope this helps...", "Feel free to ask...").
   - Use short markdown bullet points when presenting multiple items.

4. GREETINGS & SOCIAL TURNS:
   - If the user sends a greeting or asks what you can do, greet them politely, introduce yourself as HedgeDoc, and invite them to ask questions about the available documents without citing sources.
"""


def build_rag_prompt(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    history_text: str = ""
) -> str:
    """
    Encapsulates retrieved chunks from the vector store and recent conversation history into a structured prompt.

    Args:
        query: Current user question.
        retrieved_chunks: Relevant chunks retrieved from vector store.
        history_text: Formatted recent conversation history (if any).

    Returns:
        Complete prompt string ready for LLM generation.
    """
    context_blocks: List[str] = []

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        meta = chunk.get("metadata", {})
        file_name = meta.get("file_name", "Unknown Document")
        page_number = meta.get("page_number", "N/A")
        text = chunk.get("text", "").strip()

        block = (
            f"[Segment {idx}] (Document: {file_name} | Page: {page_number})\n"
            f"{text}"
        )
        context_blocks.append(block)

    context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant segments found in the documents."

    prompt_parts: List[str] = []

    if history_text.strip():
        prompt_parts.append(
            f"<chat_history>\n{history_text.strip()}\n</chat_history>\n"
        )

    prompt_parts.append(
        f"<context>\n{context_str}\n</context>\n"
    )

    prompt_parts.append(
        f"<question>\n{query.strip()}\n</question>\n\n"
        f"Answer the question above based STRICTLY on <context>. Cite your source for each claim using [Source: <file_name> - Page <page_number>] (or [Nguồn: <file_name> - Trang <page_number>] if answering in Vietnamese)."
    )

    return "\n".join(prompt_parts)
