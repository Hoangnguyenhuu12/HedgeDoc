"""
Test suite for Dual Inference Modes (Fast Mode vs Thinking Mode).
"""

import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.rag_engine import RAGEngine
from backend.prompts import STRICT_RAG_SYSTEM_PROMPT, THINKING_RAG_SYSTEM_PROMPT, build_rag_prompt


class TestInferenceModes(unittest.TestCase):
    def test_prompts_fast_vs_thinking(self):
        chunks = [{
            "text": "Điều 5. Mức chi công tác phí tối đa là 500.000 VNĐ/ngày.",
            "metadata": {
                "file_name": "chinh_sach_2025.docx",
                "page_number": 2,
                "location_label": "Điều 5: Công tác phí"
            }
        }]
        
        prompt_fast = build_rag_prompt("Mức công tác phí là bao nhiêu?", chunks, mode="fast")
        self.assertIn("<context>", prompt_fast)
        self.assertIn("Answer the question above based STRICTLY", prompt_fast)
        
        prompt_thinking = build_rag_prompt("Mức công tác phí là bao nhiêu?", chunks, mode="thinking")
        self.assertIn("<context>", prompt_thinking)
        self.assertIn("Thực hiện phân tích chuyên sâu (Thinking Mode)", prompt_thinking)
        self.assertIn("1. Tóm tắt kết luận ngắn gọn, trực diện.", prompt_thinking)

    def test_rag_engine_mode_switch(self):
        # Mock vector store, embedding, llm
        mock_vs = MagicMock()
        mock_vs.get_indexed_documents_summary.return_value = [
            {"doc_id": "doc1", "file_name": "test.pdf", "total_pages": 5, "chunk_count": 10}
        ]
        mock_vs.query.return_value = [
            {
                "chunk_id": "c1",
                "text": "Doanh thu quý 1 đạt 100 tỷ VNĐ.",
                "distance": 0.15,
                "metadata": {"file_name": "test.pdf", "page_number": 1, "location_label": "Trang 1"}
            }
        ]

        mock_llm = MagicMock()
        mock_llm.model_name = "test-llm"
        mock_llm.generate.return_value = "Doanh thu là 100 tỷ VNĐ."

        mock_emb = MagicMock()
        mock_emb.embed_text.return_value = [0.1] * 768

        engine = RAGEngine(vector_store=mock_vs, llm=mock_llm, embedding=mock_emb)

        # Test Fast Mode
        res_fast = engine.query("Doanh thu quý 1?", mode="fast", stream=False)
        self.assertEqual(res_fast["mode"], "fast")
        self.assertIn("Phân tích:", res_fast["thought_process"])

        # Test Thinking Mode
        res_thinking = engine.query("Doanh thu quý 1?", mode="thinking", stream=False)
        self.assertEqual(res_thinking["mode"], "thinking")
        self.assertIn("Chuỗi Suy Luận Chuyên Sâu", res_thinking["thought_process"])
        self.assertIn("1. **Phân tích mục tiêu & Phân rã câu hỏi**", res_thinking["thought_process"])
        self.assertIn("4. **Tổng hợp giải pháp có cấu trúc**", res_thinking["thought_process"])


if __name__ == "__main__":
    unittest.main()
