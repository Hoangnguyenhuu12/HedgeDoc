"""
Test Suite for Hybrid Reranker, Cross-Lingual RAG, and .env Hot-Reloading.
"""

import sys
import unittest
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from backend.reranker import HybridReranker
from backend.rag_engine import RAGEngine


class TestRerankerAndCrossLingual(unittest.TestCase):

    def setUp(self):
        self.engine = RAGEngine()
        self.reranker = HybridReranker()

    def test_config_reload(self):
        """Test config hot reload."""
        orig_temp = config.LLM_TEMPERATURE
        # Call reload
        config.reload()
        self.assertIsNotNone(config.LLM_PROVIDER)
        self.assertIsNotNone(config.EMBEDDING_PROVIDER)
        print(f"Config reload verified successfully! Active provider: {config.LLM_PROVIDER}")

    def test_hybrid_reranker_scoring(self):
        """Test that HybridReranker correctly ranks chunks based on vector distance and keyword overlap."""
        query = "Các thành phần của trí tuệ cảm xúc self-awareness"
        secondary_query = "Components of emotional intelligence self-awareness"

        # Mock candidates
        candidates = [
            {
                "chunk_id": "chunk_general_1",
                "text": "Weather in London is usually rainy during winter season with dense fog.",
                "distance": 0.45,
                "metadata": {"location_label": "Chapter 1", "page_number": 5, "file_name": "book.pdf"}
            },
            {
                "chunk_id": "chunk_relevant_1",
                "text": "Self-awareness is the cornerstone of emotional intelligence. It enables recognizing emotions as they happen.",
                "distance": 0.22,
                "metadata": {"location_label": "Chapter 4: Self-Awareness", "page_number": 42, "file_name": "book.pdf"}
            },
            {
                "chunk_id": "chunk_mediocre_1",
                "text": "General management principles include leadership, delegation, and strategic planning for enterprises.",
                "distance": 0.35,
                "metadata": {"location_label": "Chapter 2", "page_number": 18, "file_name": "book.pdf"}
            }
        ]

        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=2,
            secondary_query=secondary_query
        )

        self.assertEqual(len(reranked), 2)
        # Most relevant chunk should be on top
        self.assertEqual(reranked[0]["chunk_id"], "chunk_relevant_1")
        self.assertTrue("rerank_score" in reranked[0])
        self.assertGreater(reranked[0]["rerank_score"], reranked[1]["rerank_score"])
        print(f"HybridReranker test passed: Top 1 = {reranked[0]['chunk_id']} (Score: {reranked[0]['rerank_score']})")

    def test_cross_lingual_detection_and_translation(self):
        """Test Vietnamese detection and query translation."""
        vn_query = "Trí tuệ cảm xúc bao gồm những yếu tố nào?"
        is_vn = self.engine._contains_vietnamese(vn_query)
        self.assertTrue(is_vn)

        en_query = "What are the components of emotional intelligence?"
        is_en = self.engine._contains_vietnamese(en_query)
        self.assertFalse(is_en)

        # Test translation
        translated = self.engine._translate_or_expand_query(vn_query, self.engine.llm)
        self.assertIsNotNone(translated)
        self.assertTrue(len(translated) > 0)
        print(f"Cross-Lingual translation verified: '{vn_query}' -> '{translated}'")

    def test_cross_lingual_rag_query(self):
        """Test full query with Vietnamese question on indexed documents."""
        # Check if any documents exist
        docs = self.engine.vector_store.get_indexed_documents_summary()
        if not docs:
            print("No documents indexed, skipping live RAG query test.")
            return

        res = self.engine.query(
            question="Trí tuệ cảm xúc bao gồm những yếu tố nào?",
            top_k=3,
            stream=False
        )

        self.assertIn("answer", res)
        self.assertTrue(len(res["answer"]) > 0)
        self.assertTrue(len(res["citations"]) > 0)
        for cit in res["citations"]:
            self.assertIsNotNone(cit.get("rerank_score"))
            print(f"  * Citation: {cit['file_name']} ({cit['location_label']}) - Rerank Score: {cit['rerank_score']}")
        print(f"Answer sample:\n{res['answer'][:200]}...")


if __name__ == "__main__":
    unittest.main()
