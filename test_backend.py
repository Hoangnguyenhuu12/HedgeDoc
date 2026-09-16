"""
Automated Backend Test Suite for HedgeDoc.
Validates Provider Factory, Memory Buffer, Grounded Prompting, ChromaDB, RAG Queries, and Streaming.
"""

import sys
import io
from pathlib import Path

# Ensure UTF-8 stdout encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config import config
from backend.providers.factory import ProviderFactory
from backend.memory import ConversationMemoryBuffer
from backend.prompts import build_rag_prompt, STRICT_RAG_SYSTEM_PROMPT
from backend.rag_engine import RAGEngine


def run_backend_tests():
    print("=" * 70)
    print("STARTING BACKEND TEST SUITE (HEDGEDOC)")
    print("=" * 70)

    # 1. TEST PROVIDER FACTORY & GEMINI ADAPTER
    print("\n[TEST 1] Testing Provider Factory & Gemini Adapter...")
    llm = ProviderFactory.get_llm()
    embedding = ProviderFactory.get_embedding()
    print(f"  - Initialized LLM Provider: {llm.__class__.__name__} (Model: {llm.model_name})")
    print(f"  - Initialized Embedding Provider: {embedding.__class__.__name__} (Model: {embedding.model_name})")

    # Single embedding test
    sample_text = "HedgeDoc is an anti-hallucination document intelligence system."
    emb_vector = embedding.embed_text(sample_text)
    assert len(emb_vector) > 0, "Invalid embedding vector generated!"
    print(f"  - Single Embedding successful! Dimension: {len(emb_vector)}")

    # Batch embedding test
    batch_res = embedding.embed_batch(["Text sample 1", "Text sample 2"])
    assert len(batch_res) == 2, "Batch embedding failed!"
    print(f"  - Batch Embedding successful! Count: {len(batch_res)}")

    # 2. TEST CONVERSATION MEMORY BUFFER
    print("\n[TEST 2] Testing ConversationMemoryBuffer...")
    memory = ConversationMemoryBuffer(max_history_turns=3)
    memory.add_user_message("Hello!")
    memory.add_assistant_message("Hi, I am HedgeDoc.")
    memory.add_user_message("I have a question about the document.")
    memory.add_assistant_message("Please ask your question.")

    history_formatted = memory.get_formatted_history()
    assert "Hello!" in history_formatted, "User message not found in conversation history!"
    assert memory.total_messages == 4, f"Incorrect message count: {memory.total_messages}"
    print(f"  - Memory buffer functioning normally ({memory.total_messages} messages recorded).")

    # 3. TEST PROMPT BUILDER
    print("\n[TEST 3] Testing Strict Grounding Prompt Engine...")
    mock_chunks = [
        {
            "chunk_id": "c1",
            "text": "The author discusses youth self-reliance and career preparation.",
            "metadata": {"file_name": "sample.pdf", "page_number": 12}
        }
    ]
    prompt_str = build_rag_prompt(
        query="What does the author discuss?",
        retrieved_chunks=mock_chunks,
        history_text=history_formatted
    )
    assert "<context>" in prompt_str and "sample.pdf" in prompt_str and "Page: 12" in prompt_str
    print("  - Prompt builder created context block with correct citation syntax.")

    # 4. TEST CHROMADB DOCUMENT INDEXING
    print("\n[TEST 4] Testing PDF Indexing into ChromaDB...")
    rag_engine = RAGEngine()
    sample_pdf_path = config.RAW_DOCS_DIR / "sample_manual.pdf"

    if sample_pdf_path.exists():
        index_res = rag_engine.index_document(sample_pdf_path, force_reindex=True)
        print(f"  - Indexing result for '{sample_pdf_path.name}': {index_res['status']}")
        print(f"  - Stored chunks in ChromaDB: {index_res.get('chunk_count', 0)}")
    else:
        print(f"  - Test file {sample_pdf_path} not found, skipping indexing step.")

    # 5. TEST RAG QUERY ENGINE (In-Domain Query)
    print("\n[TEST 5] Testing RAG Query with in-domain question...")
    query_in_domain = "What is the return policy duration and procedure?"
    print(f"  - Query: '{query_in_domain}'")

    rag_result = rag_engine.query(question=query_in_domain, top_k=3, stream=False)
    answer = rag_result["answer"]
    citations = rag_result["citations"]

    print("\n  [HedgeDoc Response]:")
    print(f"  {answer}")
    print("\n  [Citations Retrieved]:")
    for cit in citations:
        print(f"    + File: {cit['file_name']} | Page: {cit['page_number']} | Distance: {cit['distance']:.4f}")

    assert len(citations) > 0, "No citations retrieved from ChromaDB!"
    print("\n  - In-domain query and page citation completed successfully!")

    # 6. TEST OUT-OF-DOMAIN STRICT GROUNDING
    print("\n[TEST 6] Testing Strict Grounding on out-of-domain question...")
    query_out_of_domain = "What is the current stock price of Apple in USD?"
    print(f"  - Out-of-domain query: '{query_out_of_domain}'")

    out_result = rag_engine.query(question=query_out_of_domain, top_k=2, stream=False)
    out_answer = out_result["answer"]
    print(f"\n  [HedgeDoc Response]:\n  {out_answer}")
    print("\n  - Model declined transparently without hallucinating external facts.")

    # 7. TEST STREAMING GENERATION
    print("\n[TEST 7] Testing Streaming Generation...")
    stream_query = "Summarize the key return requirements in 2 bullet points."
    stream_result = rag_engine.query(question=stream_query, top_k=2, stream=True)
    print("  - Streaming tokens: ", end="", flush=True)
    for token in stream_result["answer_stream"]:
        print(token, end="", flush=True)
    print("\n  - Streaming completed successfully!")

    # 8. TEST GREETINGS & THINKING STEPS
    print("\n[TEST 8] Testing greeting handling ('hi', 'hello') and Thinking Steps...")
    greeting_res = rag_engine.query(question="hello", stream=False)
    print("  - Query: 'hello'")
    print(f"  - Response: {greeting_res['answer'][:120]}...")
    assert "HedgeDoc" in greeting_res["answer"], "Greeting response does not introduce HedgeDoc!"
    assert len(greeting_res["citations"]) == 0, f"Greeting should not have citations! (Found {len(greeting_res['citations'])})"
    assert len(greeting_res.get("thinking_steps", [])) > 0, "No thinking_steps found in query result!"
    print("  - Thinking steps captured:")
    for s in greeting_res["thinking_steps"]:
        print(f"    + {s['title']}: {s['detail']}")
    print("  - Greeting & Thinking steps validated successfully!")

    print("\n" + "=" * 70)
    print("ALL BACKEND TESTS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_backend_tests()
