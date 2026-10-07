"""
Research Agent (Document Retrieval & Synthesis Specialist).
Focuses strictly on deep semantic retrieval, factual verification,
and document-grounded answer generation with page-level citations.
"""

from typing import Any, Dict, List, Optional
from HedgeDoc.services.rag_client import RAGClient


RESEARCH_SYSTEM_PROMPT = """\
Bạn là Chuyên gia Nghiên cứu và Tra cứu Tài liệu chuyên sâu của HedgeDoc (Document Research Specialist).
Nhiệm vụ duy nhất của bạn là: Trả lời câu hỏi của người dùng DỰA HOÀN TOÀN VÀO CÁC ĐOẠN TRÍCH TÀI LIỆU ĐƯỢC CUNG CẤP.

NGUYÊN TẮC BẮT BUỘC:
1. KHÔNG SUY DIỄN / KHÔNG BỊA ĐẶT (ZERO HALLUCINATION): Chỉ dùng thông tin có căn cứ từ đoạn trích.
2. NÊU RÕ DẪN CHỨNG: Chỉ rõ tài liệu nào, trang số mấy hoặc điều khoản nào.
3. NẾU THIẾU DỮ LIỆU: Nếu đoạn trích không đủ cơ sở để trả lời, trả lời chính xác: "NOT_FOUND".
4. ĐI THẲNG VÀO NỘI DUNG: Trả lời mạch lạc, súc tích, cấu trúc phân tích chuyên sâu.
"""


class ResearchAgent:
    """Document research specialist executing deep hybrid retrieval and evidence synthesis."""

    def __init__(self, rag_client: Optional[RAGClient] = None):
        self.rag_client = rag_client or RAGClient()

    def research(
        self,
        query: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes hybrid retrieval and generates evidence-grounded answer.
        Returns:
            Dict containing answer, citations, found (bool), and metadata.
        """
        try:
            res = self.rag_client.query(
                query_text=query,
                top_k=top_k,
                chat_history=chat_history
            )
            raw_answer = res.get("answer", "").strip()
            citations = res.get("citations", [])

            # Check if RAG completely failed to find any relevant evidence
            clean_ans = raw_answer.lower().strip()
            is_empty_rejection = (
                not citations
                or raw_answer == "NOT_FOUND"
                or (clean_ans.startswith("tài liệu hiện có không chứa thông tin về câu hỏi này") and len(clean_ans) < 90)
            )

            if is_empty_rejection:
                return {
                    "found": False,
                    "answer": "",
                    "citations": citations,
                    "raw_response": res
                }

            return {
                "found": True,
                "answer": raw_answer,
                "citations": citations,
                "raw_response": res
            }

        except Exception as exc:
            return {
                "found": False,
                "answer": "",
                "citations": [],
                "error": str(exc)
            }

    def stream_research(
        self,
        query: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes hybrid retrieval and returns citations + token generator for streaming.
        """
        try:
            citations, stream_gen = self.rag_client.stream_query(
                query_text=query,
                top_k=top_k,
                chat_history=chat_history
            )

            if not citations:
                return {
                    "found": False,
                    "citations": [],
                    "stream": None
                }

            return {
                "found": True,
                "citations": citations,
                "stream": stream_gen
            }
        except Exception as exc:
            return {
                "found": False,
                "citations": [],
                "error": str(exc),
                "stream": None
            }

