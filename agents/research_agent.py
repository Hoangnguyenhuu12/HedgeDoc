from typing import Any, Dict, List, Optional
from HedgeDoc.services.rag_client import RAGClient
from .language_utils import clean_doc_title, extract_followup_suggestions


RESEARCH_SYSTEM_PROMPT = """\
Bạn là Chuyên gia Nghiên cứu và Tra cứu Tài liệu chuyên sâu của HedgeDoc (Document Research Specialist).
Nhiệm vụ của bạn là: Khai thác, phân tích và trả lời câu hỏi của người dùng DỰA VÀO CÁC ĐOẠN TRÍCH TÀI LIỆU ĐƯỢC CUNG CẤP.

NGUYÊN TẮC BẮT BUỘC:
1. CĂN CỨ VÀO TÀI LIỆU: Mọi luận điểm, sự kiện và số liệu phải bắt nguồn từ các đoạn trích. Không bịa đặt thông tin.
2. TỔNG HỢP MẠCH LẠC: Khi người dùng yêu cầu tóm tắt hoặc tổng quan, hãy liên kết các đoạn trích để trình bày bức tranh toàn cảnh rõ ràng, đầy đủ.
3. NÊU RÕ DẪN CHỨNG: Chỉ rõ tài liệu nào, trang số mấy hoặc điều khoản nào.
4. ĐI THẲNG VÀO NỘI DUNG: Trả lời mạch lạc, súc tích, cấu trúc phân tích chuyên sâu.
5. PHẢN CHIẾU NGÔN NGỮ (LANGUAGE MIRRORING): Trả lời đúng theo ngôn ngữ người dùng hỏi (hỏi bằng tiếng Anh trả lời bằng tiếng Anh, hỏi bằng tiếng Việt trả lời bằng tiếng Việt).
"""


class ResearchAgent:
    """Document research specialist executing deep hybrid retrieval and evidence synthesis."""

    def __init__(self, rag_client: Optional[RAGClient] = None):
        self.rag_client = rag_client or RAGClient()

    def retrieve_document_overview_context(self, doc_name: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """Retrieves early opening pages and representative thematic passages for a document."""
        citations = []
        seen_texts = set()
        try:
            pipeline = self.rag_client._get_local_pipeline()
            coll = pipeline.vector_store.get_collection(pipeline.embedding_provider.dimension)

            # 1. Opening pages (Pages 1-6)
            res_early = coll.get(where={"file_name": doc_name}, limit=40, include=["metadatas", "documents"])
            early_items = []
            for i in range(len(res_early["ids"])):
                meta = res_early["metadatas"][i]
                p = meta.get("page_number", 1)
                text = meta.get("parent_text") or res_early["documents"][i]
                if p <= 6 and text not in seen_texts:
                    seen_texts.add(text)
                    early_items.append((p, meta, text))
            early_items.sort(key=lambda x: x[0])

            for p, meta, text in early_items[:4]:
                citations.append({
                    "source": doc_name,
                    "page": p,
                    "score": round(0.95 - (p * 0.02), 2),
                    "text": text
                })

            # 2. Representative thematic chunks across the document
            thematic_cits = pipeline.retriever.retrieve(
                query="tổng quan giới thiệu thông điệp chính bài học tác phẩm",
                top_k=top_k,
                filter_doc_name=doc_name
            )
            for c in thematic_cits:
                if c.text_snippet not in seen_texts:
                    seen_texts.add(c.text_snippet)
                    citations.append({
                        "source": c.doc_name,
                        "page": c.page_number,
                        "score": c.score,
                        "text": c.text_snippet
                    })
        except Exception:
            pass

        return citations[:8]

    def _build_summary_prompt(self, doc_name: str, citations: List[Dict[str, Any]], lang: str = "vi") -> str:
        clean_title = clean_doc_title(doc_name)
        context_parts = []
        for c in citations:
            p = c.get("page", 1)
            context_parts.append(f"[Trang {p}]\n{c.get('text', '')}")
        context_str = "\n\n---\n\n".join(context_parts) if context_parts else "Nội dung tài liệu."

        if lang == "en":
            return (
                f"DOCUMENT CONTEXT FOR \"{clean_title}\":\n\n{context_str}\n\n"
                f"TASK: Provide a comprehensive, inspiring, and well-structured summary of \"{clean_title}\" based on the passages above:\n"
                f"1. **Overview & Author**: Title, author, background, and general writing tone/style.\n"
                f"2. **Core Sections & Main Lessons**: Highlight the major themes, anecdotes, and pivotal messages contained in the work.\n"
                f"3. **Practical Value**: Who this book is for and the lasting takeaway.\n\n"
                f"At the very end, provide 3 specific follow-up inquiry questions for the user:\n"
                f"FOLLOW-UP INQUIRIES:\n"
                f"- [Question 1]\n"
                f"- [Question 2]\n"
                f"- [Question 3]\n\n"
                f"SUMMARY:"
            )

        return (
            f"NGỮ CẢNH TRÍCH DẪN TỪ TÀI LIỆU \"{clean_title}\":\n\n{context_str}\n\n"
            f"1. **Giới thiệu tổng quan**: Tên tác phẩm, tác giả, bối cảnh và văn phong chủ đạo.\n"
            f"2. **Các chủ đề & Thông điệp cốt lõi**: Tóm lược các phần trọng tâm, câu chuyện tiêu biểu và bài học mà cuốn sách truyền tải.\n"
            f"3. **Giá trị thực tiễn & Đối tượng hướng đến**: Độc giả nhận được giá trị gì từ cuốn sách này.\n\n"
            f"Cuối cùng, hãy đưa ra 3 câu hỏi gợi ý cụ thể để người dùng có thể bấm hỏi sâu hơn:\n"
            f"GỢI Ý TRA CỨU TIẾP:\n"
            f"- [Câu hỏi 1]\n"
            f"- [Câu hỏi 2]\n"
            f"- [Câu hỏi 3]\n\n"
            f"BÀI TÓM TẮT:"
        )

    def _get_default_doc_suggestions(self, doc_name: str, lang: str = "vi") -> List[str]:
        t = clean_doc_title(doc_name).lower()
        if "tony" in t or "ca phe" in t:
            if lang == "en":
                return [
                    "What advice does Tony give about learning English?",
                    "Tony's thoughts on youth independence and career mindset",
                    "Memorable stories from Part I: Tony's Stories"
                ]
            return [
                "Tony khuyên người trẻ học ngoại ngữ như thế nào?",
                "Quan điểm của Tony về tự lập và khởi nghiệp",
                "Những câu chuyện nổi bật trong Phần I: Chuyện của Tony"
            ]
        elif "hoang tu be" in t or "prince" in t:
            if lang == "en":
                return [
                    "The meaning of the Little Prince meeting the Fox",
                    "Lessons about love, responsibility, and the Rose",
                    "Which asteroid does the Little Prince come from?"
                ]
            return [
                "Ý nghĩa cuộc gặp giữa Hoàng tử bé và Cáo",
                "Bài học về tình yêu và trách nhiệm với Bông hồng",
                "Hoàng tử bé đến từ tiểu hành tinh nào?"
            ]
        else:
            clean = clean_doc_title(doc_name)
            if lang == "en":
                return [
                    f"Summarize main chapters of {clean}",
                    f"Key facts and figures in {clean}",
                    f"What is the main conclusion of {clean}?"
                ]
            return [
                f"Tóm tắt các điểm đáng chú ý trong {clean}",
                f"Dữ liệu và căn cứ quan trọng trong {clean}",
                f"Kết luận cốt lõi của tài liệu {clean}"
            ]

    def summarize_document(
        self,
        doc_name: str,
        query: str,
        lang: str = "vi"
    ) -> Dict[str, Any]:
        """Summarizes a specific document using high-fidelity overview extraction."""
        citations = self.retrieve_document_overview_context(doc_name=doc_name)
        if not citations:
            return {
                "found": False,
                "answer": "",
                "citations": [],
                "suggested_followups": []
            }

        prompt = self._build_summary_prompt(doc_name=doc_name, citations=citations, lang=lang)
        pipeline = self.rag_client._get_local_pipeline()
        answer = pipeline.llm_provider.generate(prompt=prompt, system_prompt=RESEARCH_SYSTEM_PROMPT)

        followups = extract_followup_suggestions(answer)
        if not followups:
            followups = self._get_default_doc_suggestions(doc_name=doc_name, lang=lang)

        return {
            "found": True,
            "answer": answer,
            "citations": citations,
            "suggested_followups": followups
        }

    def stream_summarize_document(
        self,
        doc_name: str,
        query: str,
        lang: str = "vi"
    ) -> Dict[str, Any]:
        """Streams summary of a specific document with opening-page evidence."""
        citations = self.retrieve_document_overview_context(doc_name=doc_name)
        if not citations:
            return {
                "found": False,
                "citations": [],
                "stream": None,
                "suggested_followups": []
            }

        prompt = self._build_summary_prompt(doc_name=doc_name, citations=citations, lang=lang)
        pipeline = self.rag_client._get_local_pipeline()
        stream_gen = pipeline.llm_provider.stream(prompt=prompt, system_prompt=RESEARCH_SYSTEM_PROMPT)
        followups = self._get_default_doc_suggestions(doc_name=doc_name, lang=lang)

        return {
            "found": True,
            "citations": citations,
            "stream": stream_gen,
            "suggested_followups": followups
        }

    def research(
        self,
        query: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes hybrid retrieval and generates evidence-grounded answer.
        Returns:
            Dict containing answer, citations, found (bool), suggested_followups, and metadata.
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
                or (clean_ans.startswith("tài liệu hiện có không chứa thông tin") and len(clean_ans) < 120)
                or (clean_ans.startswith("the available documents do not contain") and len(clean_ans) < 120)
                or (clean_ans.startswith("the current document does not contain") and len(clean_ans) < 120)
            )

            if is_empty_rejection:
                return {
                    "found": False,
                    "answer": "",
                    "citations": citations,
                    "suggested_followups": [],
                    "raw_response": res
                }

            followups = extract_followup_suggestions(raw_answer)
            return {
                "found": True,
                "answer": raw_answer,
                "citations": citations,
                "suggested_followups": followups,
                "raw_response": res
            }

        except Exception as exc:
            return {
                "found": False,
                "answer": "",
                "citations": [],
                "suggested_followups": [],
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
                    "stream": None,
                    "suggested_followups": []
                }

            # Attempt to deduce default followups based on top citation doc
            top_doc = citations[0].get("source", "") if citations else ""
            default_followups = self._get_default_doc_suggestions(top_doc) if top_doc else []

            return {
                "found": True,
                "citations": citations,
                "stream": stream_gen,
                "suggested_followups": default_followups
            }
        except Exception as exc:
            return {
                "found": False,
                "citations": [],
                "error": str(exc),
                "stream": None,
                "suggested_followups": []
            }

