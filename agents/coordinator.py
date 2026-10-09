from typing import Any, Dict, List, Optional
from .frontdesk_agent import FrontdeskAgent
from .research_agent import ResearchAgent
from .language_utils import (
    detect_language,
    match_target_document,
    clean_doc_title,
    is_legal_inquiry,
    is_legal_document,
    is_clarification_context,
    resolve_document_from_context
)
from HedgeDoc.services.rag_client import RAGClient


class MultiAgentCoordinator:
    """Orchestrates communication between Frontdesk and Research agents."""

    def __init__(
        self,
        frontdesk_agent: Optional[FrontdeskAgent] = None,
        research_agent: Optional[ResearchAgent] = None,
        rag_client: Optional[RAGClient] = None
    ):
        self.rag_client = rag_client or RAGClient()
        self.research_agent = research_agent or ResearchAgent(rag_client=self.rag_client)

        # Share LLM provider with frontdesk agent
        llm = None
        try:
            llm = self.rag_client._get_local_pipeline().llm_provider
        except Exception:
            pass
        self.frontdesk_agent = frontdesk_agent or FrontdeskAgent(llm_provider=llm)

    def _get_catalog_suggestions(self, indexed_docs: List[Dict[str, Any]], lang: str = "vi") -> List[str]:
        """Generates quick exploration chips based on currently indexed documents."""
        if not indexed_docs:
            return []
        chips = []
        for d in indexed_docs[:3]:
            title = clean_doc_title(d.get("file_name", ""))
            if lang == "en":
                chips.append(f"Summarize the book {title}")
            else:
                chips.append(f"Tóm tắt sách {title}")
        return chips

    def process(
        self,
        query: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None,
        indexed_docs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes query through collaborative multi-agent pipeline.
        """
        indexed_docs = indexed_docs or self.rag_client.list_indexed_documents()
        lang = detect_language(query)
        matched_doc = match_target_document(query, indexed_docs)

        # Multi-turn Context Memory Resolution (e.g. following 'which book to summarize?')
        in_clarification = is_clarification_context(chat_history)
        resolved_context_doc = resolve_document_from_context(query, chat_history, indexed_docs)
        if in_clarification and resolved_context_doc:
            matched_doc = resolved_context_doc
            intent = "document_summary"
        else:
            intent = self.frontdesk_agent.classify_intent(query)
            if not matched_doc and resolved_context_doc:
                matched_doc = resolved_context_doc

        # ----------------------------------------------------------------------
        # SCENARIO 1.8: Non-Legal Document Guidance for Regulations / Terms
        # ----------------------------------------------------------------------
        has_legal_docs = any(is_legal_document(d.get("file_name", "")) for d in indexed_docs)
        if is_legal_inquiry(query) and not has_legal_docs and indexed_docs:
            if lang == "en":
                thought = (
                    "[Coordinator]: Detected legal / regulatory query for literary & self-development books.\n"
                    "-> Explaining document scope and pivoting to behavioral principles & key stories."
                )
                doc_titles = ", ".join(f"**{clean_doc_title(d['file_name'])}**" for d in indexed_docs[:3])
                answer = (
                    f"The documents currently available in the knowledge base ({doc_titles}) are literary, philosophical, "
                    f"and personal development books rather than legal statutes, corporate policies, or contracts. "
                    f"Consequently, they **do not contain formal legal articles or statutory clauses**.\n\n"
                    f"Instead, you can explore the most impactful equivalent takeaways:\n"
                    f"- **Core life principles and behavioral codes**\n"
                    f"- **Perspectives on independence, mindset, and career growth**\n"
                    f"- **Signature stories and key allegories**\n\n"
                    f"Feel free to select one of the suggested topics below:"
                )
                followups = [
                    "Life principles and behavioral lessons",
                    "Mindset on independence and career",
                    "Key stories and core messages"
                ]
            else:
                thought = (
                    "[Bộ điều phối]: Nhận diện câu hỏi tra cứu quy định / điều khoản đối với sách văn học & kỹ năng sống.\n"
                    "-> Giải thích tính chất tài liệu và chủ động gợi ý tra cứu các nguyên tắc sống & bài học ứng xử."
                )
                doc_titles = ", ".join(f"**{clean_doc_title(d['file_name'])}**" for d in indexed_docs[:3])
                answer = (
                    f"Các tài liệu hiện có trong kho tri thức ({doc_titles}) là các tác phẩm văn học, tản văn và kỹ năng sống "
                    f"thay vì văn bản pháp luật, hợp đồng hay quy chế hành chính. Do đó, tài liệu **không có các điều khoản pháp lý hoặc quy định bắt buộc**.\n\n"
                    f"Thay vào đó, bạn có thể tra cứu những nội dung tương đương và giá trị nhất của cuốn sách:\n"
                    f"- **Các nguyên tắc sống và bài học ứng xử**\n"
                    f"- **Quan điểm về tự lập, tác phong và lập nghiệp**\n"
                    f"- **Các câu chuyện tiêu biểu và thông điệp cốt lõi**\n\n"
                    f"Bạn có thể bấm vào một trong các chủ đề gợi ý ngay bên dưới để tiếp tục khám phá:"
                )
                followups = [
                    "Các nguyên tắc sống và bài học ứng xử",
                    "Quan điểm về tự lập và lập nghiệp",
                    "Các câu chuyện tiêu biểu trong sách"
                ]
            return {
                "answer": answer,
                "thought": thought,
                "citations": [],
                "suggested_followups": followups,
                "agent_route": "non_legal_guidance"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 1: Greeting, General System Info, or Workflow Guidance
        # ----------------------------------------------------------------------
        if intent == "frontdesk_chat":
            if lang == "en":
                thought = (
                    "[Coordinator]: Detected general inquiry / platform guidance in English.\n"
                    "-> Generating direct, concise response on capabilities and current knowledge base."
                )
            else:
                thought = (
                    "[Bộ điều phối]: Nhận diện câu hỏi thông tin chung / hướng dẫn hệ thống.\n"
                    "-> Phản hồi trực tiếp, súc tích về tính năng và tài liệu hiện có trong kho."
                )
            answer = self.frontdesk_agent.respond_conversational(
                query=query,
                indexed_docs=indexed_docs,
                chat_history=chat_history
            )
            return {
                "answer": answer,
                "thought": thought,
                "citations": [],
                "suggested_followups": self._get_catalog_suggestions(indexed_docs, lang),
                "agent_route": "frontdesk_direct"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 1.5: Platform Capabilities (Quality Gate & OCR)
        # ----------------------------------------------------------------------
        if intent == "platform_capabilities":
            if lang == "en":
                thought = (
                    "[Coordinator]: Detected platform capability inquiry regarding Document Quality Gate and OCR.\n"
                    "-> Presenting comprehensive inspection standards and guidance."
                )
                answer = (
                    "**HedgeDoc Document Quality Gate & OCR Inspection Standards:**\n\n"
                    "- **Sharpness (Laplacian Variance)**: Detects blur, defocus, and motion artifacts.\n"
                    "- **Contrast (RMS Contrast)**: Measures character distinction against background.\n"
                    "- **Skew & Shadow**: Identifies rotational distortion and uneven lighting.\n"
                    "- **Readiness Score (1.0 - 5.0)**: Provides actionable recommendations (*Direct to OCR*, *Enhance*, *Reject*).\n\n"
                    "To assess your documents, please upload files in the left sidebar under **Upload New Document**."
                )
                followups = ["Upload instructions", "OCR extraction formats", "Quality score criteria"]
            else:
                thought = (
                    "[Bộ điều phối]: Nhận diện câu hỏi về năng lực Kiểm định chất lượng tài liệu và Bóc tách OCR.\n"
                    "-> Cung cấp tiêu chuẩn đo lường và hướng dẫn nạp tài liệu."
                )
                answer = (
                    "**Quy trình Kiểm định chất lượng tài liệu & Bóc tách OCR của HedgeDoc:**\n\n"
                    "- **Độ sắc nét (Sharpness - Laplacian Variance)**: Đo lường độ nét, cảnh báo mờ nhòe gây lỗi ký tự.\n"
                    "- **Độ tương phản (Contrast - RMS)**: Đo khả năng tách biệt giữa chữ và phông nền scan.\n"
                    "- **Góc nghiêng & Bóng đổ (Skew & Shadow)**: Đo độ lệch trang và vùng bóng tối che khuất dữ liệu.\n"
                    "- **Điểm sẵn sàng OCR (1.0 - 5.0)**: Tự động phân hạng (*Đủ tiêu chuẩn*, *Cần tăng cường*, *Từ chối*).\n\n"
                    "Để kiểm định tài liệu của bạn: Hãy tải file lên ở thanh bên trái mục **Tải lên tài liệu mới**. Hệ thống sẽ tự động đo lường và hiển thị thẻ điểm kiểm định chi tiết."
                )
                followups = ["Hướng dẫn tải tài liệu", "Tiêu chuẩn độ nét OCR", "Quy trình bóc tách bảng biểu"]
            return {
                "answer": answer,
                "thought": thought,
                "citations": [],
                "suggested_followups": followups,
                "agent_route": "platform_capabilities"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 2: Document-Level Summarization & Overview
        # ----------------------------------------------------------------------
        if intent == "document_summary":
            # If a specific document is identified
            target = matched_doc or (indexed_docs[0] if len(indexed_docs) == 1 else None)
            if target:
                target_title = clean_doc_title(target.get("file_name", ""))
                if lang == "en":
                    thought = (
                        f"[Coordinator]: Identified document overview / summary request for \"{target_title}\".\n"
                        f"[Coordinator -> Specialist]: Extracting opening sections and core themes for structured synthesis..."
                    )
                else:
                    thought = (
                        f"[Bộ điều phối]: Nhận diện yêu cầu tóm tắt tác phẩm \"{target_title}\".\n"
                        f"[Điều phối -> Chuyên gia]: Thu thập phần mở đầu và các chương mục tiêu biểu để tổng hợp toàn diện..."
                    )
                sum_res = self.research_agent.summarize_document(
                    doc_name=target.get("file_name", ""),
                    query=query,
                    lang=lang
                )
                return {
                    "answer": sum_res.get("answer"),
                    "thought": thought,
                    "citations": sum_res.get("citations", []),
                    "suggested_followups": sum_res.get("suggested_followups", []),
                    "agent_route": "document_summary"
                }

            # If ambiguous which document to summarize
            if indexed_docs:
                doc_list = "\n".join(
                    f"{idx+1}. **{clean_doc_title(d['file_name'])}** ({d['chunk_count']} đoạn véc-tơ)"
                    for idx, d in enumerate(indexed_docs[:3])
                )
                if lang == "en":
                    answer = (
                        f"Currently, there are multiple documents available in the knowledge base:\n\n{doc_list}\n\n"
                        "Which book or document would you like me to summarize? Please select from the suggestions below or enter the document title."
                    )
                    thought = "[Coordinator]: Multiple documents found. Prompting user to specify target document."
                else:
                    answer = (
                        f"Hiện tại trong kho tri thức đang có các tài liệu sau:\n\n{doc_list}\n\n"
                        "Bạn muốn tôi tóm tắt cuốn sách hay tài liệu nào trong số trên? Vui lòng chọn bên dưới hoặc cho tôi biết tên tác phẩm bạn quan tâm."
                    )
                    thought = "[Bộ điều phối]: Nhận diện yêu cầu tóm tắt nhưng chưa rõ tài liệu cụ thể. Đang liệt kê và hỏi lại người dùng."
                return {
                    "answer": answer,
                    "thought": thought,
                    "citations": [],
                    "suggested_followups": self._get_catalog_suggestions(indexed_docs, lang),
                    "agent_route": "frontdesk_clarification"
                }

        # ----------------------------------------------------------------------
        # SCENARIO 3: Document Research & Fact Extraction
        # ----------------------------------------------------------------------
        if lang == "en":
            thought_steps = [
                "[Coordinator]: Analyzing request for factual knowledge retrieval from documents.",
                "[Coordinator -> Specialist]: Routing query to Document Research Specialist...",
            ]
        else:
            thought_steps = [
                "[Bộ điều phối]: Phân tích yêu cầu tra cứu kiến thức thực tế từ tài liệu.",
                "[Điều phối -> Chuyên gia]: Chuyển giao yêu cầu tra cứu sang Tác tử Nghiên cứu Tài liệu...",
            ]

        research_res = self.research_agent.research(
            query=query,
            top_k=top_k,
            chat_history=chat_history
        )

        if research_res.get("found"):
            if lang == "en":
                thought_steps.append(
                    f"[Research Specialist]: Found {len(research_res.get('citations', []))} citations and synthesized grounded answer from documents."
                )
            else:
                thought_steps.append(
                    f"[Tác tử Nghiên cứu]: Đã tìm thấy {len(research_res.get('citations', []))} đoạn trích dẫn và tổng hợp câu trả lời căn cứ từ tài liệu."
                )
            return {
                "answer": research_res.get("answer"),
                "thought": "\n".join(thought_steps),
                "citations": research_res.get("citations", []),
                "suggested_followups": research_res.get("suggested_followups", []),
                "agent_route": "research_specialist"
            }
        else:
            if lang == "en":
                thought_steps.append(
                    "[Research Specialist]: Insufficient grounding evidence found in current documents."
                )
                thought_steps.append(
                    "[Coordinator]: Clarifying with user and suggesting relevant topics available in the knowledge base."
                )
            else:
                thought_steps.append(
                    "[Tác tử Nghiên cứu]: Không tìm thấy đủ cơ sở dữ liệu trong các tài liệu hiện có."
                )
                thought_steps.append(
                    "[Bộ điều phối]: Làm rõ và gợi ý các chủ đề có sẵn trong kho tri thức để người dùng tiếp tục khai thác."
                )
            friendly_answer = self.frontdesk_agent.respond_not_found(
                query=query,
                indexed_docs=indexed_docs,
                matched_doc=matched_doc
            )
            fallback_followups = (
                self.research_agent._get_default_doc_suggestions(matched_doc.get("file_name", ""), lang=lang)
                if matched_doc
                else self._get_catalog_suggestions(indexed_docs, lang)
            )
            return {
                "answer": friendly_answer,
                "thought": "\n".join(thought_steps),
                "citations": research_res.get("citations", []),
                "suggested_followups": fallback_followups,
                "agent_route": "frontdesk_guidance"
            }

    def process_stream(
        self,
        query: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None,
        indexed_docs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes query through collaborative multi-agent pipeline with real-time token streaming.
        Returns:
            Dict containing thought, citations, stream (generator), suggested_followups, and agent_route.
        """
        indexed_docs = indexed_docs or self.rag_client.list_indexed_documents()
        lang = detect_language(query)
        matched_doc = match_target_document(query, indexed_docs)

        # Multi-turn Context Memory Resolution (e.g. following 'which book to summarize?')
        in_clarification = is_clarification_context(chat_history)
        resolved_context_doc = resolve_document_from_context(query, chat_history, indexed_docs)
        if in_clarification and resolved_context_doc:
            matched_doc = resolved_context_doc
            intent = "document_summary"
        else:
            intent = self.frontdesk_agent.classify_intent(query)
            if not matched_doc and resolved_context_doc:
                matched_doc = resolved_context_doc

        def _word_stream(text: str):
            words = text.split(" ")
            for idx, w in enumerate(words):
                yield w + (" " if idx < len(words) - 1 else "")

        # ----------------------------------------------------------------------
        # SCENARIO 1.8: Non-Legal Document Guidance for Regulations / Terms
        # ----------------------------------------------------------------------
        has_legal_docs = any(is_legal_document(d.get("file_name", "")) for d in indexed_docs)
        if is_legal_inquiry(query) and not has_legal_docs and indexed_docs:
            if lang == "en":
                thought = (
                    "[Coordinator]: Detected legal / regulatory query for literary & self-development books.\n"
                    "-> Explaining document scope and pivoting to behavioral principles & key stories."
                )
                doc_titles = ", ".join(f"**{clean_doc_title(d['file_name'])}**" for d in indexed_docs[:3])
                answer = (
                    f"The documents currently available in the knowledge base ({doc_titles}) are literary, philosophical, "
                    f"and personal development books rather than legal statutes, corporate policies, or contracts. "
                    f"Consequently, they **do not contain formal legal articles or statutory clauses**.\n\n"
                    f"Instead, you can explore the most impactful equivalent takeaways:\n"
                    f"- **Core life principles and behavioral codes**\n"
                    f"- **Perspectives on independence, mindset, and career growth**\n"
                    f"- **Signature stories and key allegories**\n\n"
                    f"Feel free to select one of the suggested topics below:"
                )
                followups = [
                    "Life principles and behavioral lessons",
                    "Mindset on independence and career",
                    "Key stories and core messages"
                ]
            else:
                thought = (
                    "[Bộ điều phối]: Nhận diện câu hỏi tra cứu quy định / điều khoản đối với sách văn học & kỹ năng sống.\n"
                    "-> Giải thích tính chất tài liệu và chủ động gợi ý tra cứu các nguyên tắc sống & bài học ứng xử."
                )
                doc_titles = ", ".join(f"**{clean_doc_title(d['file_name'])}**" for d in indexed_docs[:3])
                answer = (
                    f"Các tài liệu hiện có trong kho tri thức ({doc_titles}) là các tác phẩm văn học, tản văn và kỹ năng sống "
                    f"thay vì văn bản pháp luật, hợp đồng hay quy chế hành chính. Do đó, tài liệu **không có các điều khoản pháp lý hoặc quy định bắt buộc**.\n\n"
                    f"Thay vào đó, bạn có thể tra cứu những nội dung tương đương và giá trị nhất của cuốn sách:\n"
                    f"- **Các nguyên tắc sống và bài học ứng xử**\n"
                    f"- **Quan điểm về tự lập, tác phong và lập nghiệp**\n"
                    f"- **Các câu chuyện tiêu biểu và thông điệp cốt lõi**\n\n"
                    f"Bạn có thể bấm vào một trong các chủ đề gợi ý ngay bên dưới để tiếp tục khám phá:"
                )
                followups = [
                    "Các nguyên tắc sống và bài học ứng xử",
                    "Quan điểm về tự lập và lập nghiệp",
                    "Các câu chuyện tiêu biểu trong sách"
                ]
            return {
                "thought": thought,
                "citations": [],
                "stream": _word_stream(answer),
                "suggested_followups": followups,
                "agent_route": "non_legal_guidance"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 1: Greeting, General System Info, or Workflow Guidance
        # ----------------------------------------------------------------------
        if intent == "frontdesk_chat":
            if lang == "en":
                thought = (
                    "[Coordinator]: Detected general inquiry / platform guidance in English.\n"
                    "-> Generating direct, concise response on capabilities and current knowledge base."
                )
            else:
                thought = (
                    "[Bộ điều phối]: Nhận diện câu hỏi thông tin chung / hướng dẫn hệ thống.\n"
                    "-> Phản hồi trực tiếp, súc tích về tính năng và tài liệu hiện có trong kho."
                )
            answer = self.frontdesk_agent.respond_conversational(
                query=query,
                indexed_docs=indexed_docs,
                chat_history=chat_history
            )
            return {
                "thought": thought,
                "citations": [],
                "stream": _word_stream(answer),
                "suggested_followups": self._get_catalog_suggestions(indexed_docs, lang),
                "agent_route": "frontdesk_direct"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 1.5: Platform Capabilities (Quality Gate & OCR)
        # ----------------------------------------------------------------------
        if intent == "platform_capabilities":
            if lang == "en":
                thought = (
                    "[Coordinator]: Detected platform capability inquiry regarding Document Quality Gate and OCR.\n"
                    "-> Presenting comprehensive inspection standards and guidance."
                )
                answer = (
                    "**HedgeDoc Document Quality Gate & OCR Inspection Standards:**\n\n"
                    "- **Sharpness (Laplacian Variance)**: Detects blur, defocus, and motion artifacts.\n"
                    "- **Contrast (RMS Contrast)**: Measures character distinction against background.\n"
                    "- **Skew & Shadow**: Identifies rotational distortion and uneven lighting.\n"
                    "- **Readiness Score (1.0 - 5.0)**: Provides actionable recommendations (*Direct to OCR*, *Enhance*, *Reject*).\n\n"
                    "To assess your documents, please upload files in the left sidebar under **Upload New Document**."
                )
                followups = ["Upload instructions", "OCR extraction formats", "Quality score criteria"]
            else:
                thought = (
                    "[Bộ điều phối]: Nhận diện câu hỏi về năng lực Kiểm định chất lượng tài liệu và Bóc tách OCR.\n"
                    "-> Cung cấp tiêu chuẩn đo lường và hướng dẫn nạp tài liệu."
                )
                answer = (
                    "**Quy trình Kiểm định chất lượng tài liệu & Bóc tách OCR của HedgeDoc:**\n\n"
                    "- **Độ sắc nét (Sharpness - Laplacian Variance)**: Đo lường độ nét, cảnh báo mờ nhòe gây lỗi ký tự.\n"
                    "- **Độ tương phản (Contrast - RMS)**: Đo khả năng tách biệt giữa chữ và phông nền scan.\n"
                    "- **Góc nghiêng & Bóng đổ (Skew & Shadow)**: Đo độ lệch trang và vùng bóng tối che khuất dữ liệu.\n"
                    "- **Điểm sẵn sàng OCR (1.0 - 5.0)**: Tự động phân hạng (*Đủ tiêu chuẩn*, *Cần tăng cường*, *Từ chối*).\n\n"
                    "Để kiểm định tài liệu của bạn: Hãy tải file lên ở thanh bên trái mục **Tải lên tài liệu mới**. Hệ thống sẽ tự động đo lường và hiển thị thẻ điểm kiểm định chi tiết."
                )
                followups = ["Hướng dẫn tải tài liệu", "Tiêu chuẩn độ nét OCR", "Quy trình bóc tách bảng biểu"]
            return {
                "thought": thought,
                "citations": [],
                "stream": _word_stream(answer),
                "suggested_followups": followups,
                "agent_route": "platform_capabilities"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 2: Document-Level Summarization & Overview
        # ----------------------------------------------------------------------
        if intent == "document_summary":
            target = matched_doc or (indexed_docs[0] if len(indexed_docs) == 1 else None)
            if target:
                target_title = clean_doc_title(target.get("file_name", ""))
                if lang == "en":
                    thought = (
                        f"[Coordinator]: Identified document overview / summary request for \"{target_title}\".\n"
                        f"[Coordinator -> Specialist]: Extracting opening sections and core themes for structured synthesis..."
                    )
                else:
                    thought = (
                        f"[Bộ điều phối]: Nhận diện yêu cầu tóm tắt tác phẩm \"{target_title}\".\n"
                        f"[Điều phối -> Chuyên gia]: Thu thập phần mở đầu và các chương mục tiêu biểu để tổng hợp toàn diện..."
                    )
                sum_res = self.research_agent.stream_summarize_document(
                    doc_name=target.get("file_name", ""),
                    query=query,
                    lang=lang
                )
                return {
                    "thought": thought,
                    "citations": sum_res.get("citations", []),
                    "stream": sum_res.get("stream"),
                    "suggested_followups": sum_res.get("suggested_followups", []),
                    "agent_route": "document_summary"
                }

            # If ambiguous which document to summarize
            if indexed_docs:
                doc_list = "\n".join(
                    f"{idx+1}. **{clean_doc_title(d['file_name'])}** ({d['chunk_count']} đoạn véc-tơ)"
                    for idx, d in enumerate(indexed_docs[:3])
                )
                if lang == "en":
                    answer = (
                        f"Currently, there are multiple documents available in the knowledge base:\n\n{doc_list}\n\n"
                        "Which book or document would you like me to summarize? Please select from the suggestions below or enter the document title."
                    )
                    thought = "[Coordinator]: Multiple documents found. Prompting user to specify target document."
                else:
                    answer = (
                        f"Hiện tại trong kho tri thức đang có các tài liệu sau:\n\n{doc_list}\n\n"
                        "Bạn muốn tôi tóm tắt cuốn sách hay tài liệu nào trong số trên? Vui lòng chọn bên dưới hoặc cho tôi biết tên tác phẩm bạn quan tâm."
                    )
                    thought = "[Bộ điều phối]: Nhận diện yêu cầu tóm tắt nhưng chưa rõ tài liệu cụ thể. Đang liệt kê và hỏi lại người dùng."
                return {
                    "thought": thought,
                    "citations": [],
                    "stream": _word_stream(answer),
                    "suggested_followups": self._get_catalog_suggestions(indexed_docs, lang),
                    "agent_route": "frontdesk_clarification"
                }

        # ----------------------------------------------------------------------
        # SCENARIO 3: Document Research & Fact Extraction
        # ----------------------------------------------------------------------
        if lang == "en":
            thought_steps = [
                "[Coordinator]: Analyzing request for factual knowledge retrieval from documents.",
                "[Coordinator -> Specialist]: Routing query to Document Research Specialist...",
            ]
        else:
            thought_steps = [
                "[Bộ điều phối]: Phân tích yêu cầu tra cứu kiến thức thực tế từ tài liệu.",
                "[Điều phối -> Chuyên gia]: Chuyển giao yêu cầu tra cứu sang Tác tử Nghiên cứu Tài liệu...",
            ]

        research_res = self.research_agent.stream_research(
            query=query,
            top_k=top_k,
            chat_history=chat_history
        )

        if research_res.get("found"):
            citations = research_res.get("citations", [])
            if lang == "en":
                thought_steps.append(
                    f"[Research Specialist]: Found {len(citations)} citations and streaming grounded response in real time."
                )
            else:
                thought_steps.append(
                    f"[Tác tử Nghiên cứu]: Đã tìm thấy {len(citations)} đoạn trích dẫn và truyền dữ liệu thời gian thực căn cứ từ tài liệu."
                )
            return {
                "thought": "\n".join(thought_steps),
                "citations": citations,
                "stream": research_res.get("stream"),
                "suggested_followups": research_res.get("suggested_followups", []),
                "agent_route": "research_specialist"
            }
        else:
            if lang == "en":
                thought_steps.append(
                    "[Research Specialist]: Insufficient grounding evidence found in current documents."
                )
                thought_steps.append(
                    "[Coordinator]: Clarifying with user and suggesting relevant topics available in the knowledge base."
                )
            else:
                thought_steps.append(
                    "[Tác tử Nghiên cứu]: Không tìm thấy đủ cơ sở dữ liệu trong các tài liệu hiện có."
                )
                thought_steps.append(
                    "[Bộ điều phối]: Làm rõ và gợi ý các chủ đề có sẵn trong kho tri thức để người dùng tiếp tục khai thác."
                )
            friendly_answer = self.frontdesk_agent.respond_not_found(
                query=query,
                indexed_docs=indexed_docs,
                matched_doc=matched_doc
            )
            fallback_followups = (
                self.research_agent._get_default_doc_suggestions(matched_doc.get("file_name", ""), lang=lang)
                if matched_doc
                else self._get_catalog_suggestions(indexed_docs, lang)
            )
            return {
                "thought": "\n".join(thought_steps),
                "citations": research_res.get("citations", []),
                "stream": _word_stream(friendly_answer),
                "suggested_followups": fallback_followups,
                "agent_route": "frontdesk_guidance"
            }

    def _get_catalog_suggestions(self, indexed_docs: List[Dict[str, Any]], lang: str = "vi") -> List[str]:
        """Generates general or catalog-based follow-up chips fitting on 1 row."""
        if not indexed_docs:
            if lang == "en":
                return ["Upload new document", "OCR Inspection standards"]
            return ["Hướng dẫn nạp tài liệu", "Tiêu chuẩn kiểm định OCR"]

        suggestions = []
        for d in indexed_docs[:3]:
            title = clean_doc_title(d.get("file_name", ""))
            if lang == "en":
                suggestions.append(f"Summarize {title}")
            else:
                suggestions.append(f"Tóm tắt {title}")
        return suggestions

