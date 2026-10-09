"""
Frontdesk Agent (Receptionist & User Guide).
Handles conversational greetings, onboarding, user instructions,
and coordinates with specialized downstream agents.
"""

from typing import Any, Dict, List, Optional
import re
from .language_utils import detect_language, is_summarization_query, clean_doc_title


FRONTDESK_SYSTEM_PROMPT_VI = """\
Bạn là HedgeDoc — Trợ lý AI Khai thác & Quản lý Tri thức Tài liệu.

NGUYÊN TẮC PHẢN HỒI (BẮT BUỘC):
1. TUYỆT ĐỐI KHÔNG tự xưng là lễ tân, nhân viên điều phối hay thu ngân. Tự xưng là "HedgeDoc" hoặc "Tôi".
2. Trả lời NGẮN GỌN, ĐÚNG TRỌNG TÂM, ĐI THẲNG VÀO Ý CHÍNH, không dài dòng xã giao.
3. Khi người dùng hỏi bạn là ai: Trả lời:
   Tôi là **HedgeDoc** — Nền tảng Trí tuệ và Khai phá Tri thức Tài liệu.

   **Khả năng chính:**
   - **Kiểm định chất lượng**: Đo lường độ nét, tương phản, độ phân giải tài liệu trước khi bóc tách.
   - **Bóc tách OCR**: Trích xuất chính xác văn bản số, bảng biểu và cấu trúc dữ liệu.
   - **Tra cứu thông minh**: Phân đoạn, lập chỉ mục véc-tơ và trả lời câu hỏi trực tiếp từ tài liệu đã nạp.
4. Khi người dùng chào hỏi: Chào ngắn gọn 1 câu và sẵn sàng hỗ trợ tra cứu.
5. Khi người dùng hỏi cách dùng: Hướng dẫn súc tích các bước (Tải tài liệu ở thanh bên -> Nạp vào kho -> Đặt câu hỏi tra cứu).
6. Khi người dùng hỏi về tài liệu trong kho: Liệt kê ngắn gọn danh sách tài liệu hiện có.
"""

FRONTDESK_SYSTEM_PROMPT_EN = """\
You are HedgeDoc — Intelligent Document Processing & Knowledge Discovery Platform Assistant.

STRICT PRINCIPLES:
1. NEVER refer to yourself as a receptionist, coordinator, or cashier. Self-identify as "HedgeDoc" or "I".
2. Respond CONCISELY, ACCURATELY, and DIRECTLY to the user's intent.
3. When asked who you are, respond:
   I am **HedgeDoc** — Intelligent Document Processing & Knowledge Discovery Platform.

   **Core Capabilities:**
   - **Quality Assessment**: Evaluates sharpness, contrast, and resolution of documents prior to extraction.
   - **OCR Extraction**: Accurately extracts digital text, structured tables, and content blocks.
   - **Smart Retrieval**: Chunks, vector-indexes, and answers queries directly from ingested documents.
4. When greeted, greet politely in 1 concise sentence.
5. When asked for usage instructions, guide briefly (Upload on the sidebar -> Ingest into knowledge base -> Ask queries).
6. When asked about documents, clearly list the files currently in the knowledge base.
"""


class FrontdeskAgent:
    """Conversational assistant handling greeting, orientation, and direct inquiries with Language Mirroring."""

    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    def classify_intent(self, query: str) -> str:
        """
        Classifies whether user query is a general/social question or a document research query.
        Supports both Vietnamese and English intents.
        """
        q = query.strip().lower()

        # Common greeting & conversational patterns in Vietnamese & English
        greetings = [
            # Vietnamese
            r"^(hi|hello|helo|hey|chào|xin chào|halo|alo)\b",
            r"^(bạn là ai|bạn tên gì|bạn có thể làm gì|bạn giúp được gì)\b",
            r"^(hướng dẫn|cách dùng|làm sao để|cách nạp|thêm file|tải file)\b",
            r"^(trong kho có gì|có những sách nào|danh sách tài liệu|tài liệu nào)\b",
            r"^(cảm ơn|thank you|thanks|tạm biệt|bye)\b",
            # English
            r"^(who are you|what are you|what can you do|how can you help|tell me about yourself|introduce yourself)\b",
            r"^(how to use|how does it work|how to upload|how do i upload|guide|help)\b",
            r"^(what documents|list documents|what files|which files|show documents|what is in the store)\b",
            r"^(thank you|thanks|bye|goodbye)\b"
        ]

        for pattern in greetings:
            if re.search(pattern, q):
                return "frontdesk_chat"

        # Check for quality assessment or OCR platform questions
        quality_patterns = [
            r"(kiểm định chất lượng|đo độ nét|độ tương phản|bóng đổ|chất lượng scan|kiểm định tài liệu|tiêu chuẩn ocr|bóc tách ocr|khả năng ocr)",
            r"(quality gate|document quality|sharpness|contrast|ocr assessment|ocr extraction)"
        ]
        if any(re.search(p, q) for p in quality_patterns):
            return "platform_capabilities"

        # Check for document summary / overview request
        if is_summarization_query(q):
            return "document_summary"

        # If very short query with no context (<= 2 words)
        words = q.split()
        if len(words) <= 2 and any(w in ("hi", "hello", "chào", "alo", "helo", "hey") for w in words):
            return "frontdesk_chat"

        return "document_research"

    def respond_conversational(
        self,
        query: str,
        indexed_docs: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generates a concise, informative response adapting to query language (EN / VI).
        """
        q_lower = query.lower().strip()
        lang = detect_language(query)

        # 1. Tra cứu danh tính (Identity inquiry)
        is_identity_query = (
            any(w in q_lower for w in ("bạn là", "là ai", "tên gì"))
            or re.search(r"\b(who are you|what are you|who r u|introduce yourself)\b", q_lower)
            or (lang == "en" and "who" in q_lower and "you" in q_lower)
            or (lang == "vi" and "ai" in q_lower and ("bạn" in q_lower or "mày" in q_lower or "em" in q_lower))
        )
        if is_identity_query:
            if lang == "en":
                return (
                    "I am **HedgeDoc** — Intelligent Document Processing & Knowledge Discovery Platform.\n\n"
                    "**Core Capabilities:**\n\n"
                    "- **Quality Assessment**: Evaluates sharpness, contrast, and resolution of documents prior to extraction.\n"
                    "- **OCR Extraction**: Accurately extracts digital text, structured tables, and content blocks.\n"
                    "- **Smart Retrieval**: Chunks, vector-indexes, and answers queries directly from ingested documents."
                )
            return (
                "Tôi là **HedgeDoc** — Nền tảng Trí tuệ và Khai phá Tri thức Tài liệu.\n\n"
                "**Khả năng chính:**\n\n"
                "- **Kiểm định chất lượng**: Đo lường độ nét, tương phản, độ phân giải tài liệu trước khi bóc tách.\n"
                "- **Bóc tách OCR**: Trích xuất chính xác văn bản số, bảng biểu và cấu trúc dữ liệu.\n"
                "- **Tra cứu thông minh**: Phân đoạn, lập chỉ mục véc-tơ và trả lời câu hỏi trực tiếp từ tài liệu đã nạp."
            )

        # 2. Chào hỏi thông thường (Greetings)
        is_greeting = any(w in q_lower for w in ("hi", "hello", "hey", "chào", "xin chào", "greetings"))
        if is_greeting:
            if lang == "en":
                return (
                    "Hello! I am **HedgeDoc**.\n\n"
                    "I can assist you with document quality inspection, OCR extraction, and grounded factual retrieval from your ingested files. Feel free to ask questions or upload new files on the left sidebar!"
                )
            return (
                "Xin chào! Tôi là **HedgeDoc**.\n\n"
                "Tôi có thể hỗ trợ bạn kiểm định chất lượng, bóc tách OCR và tra cứu thông tin chính xác từ các tài liệu được nạp vào hệ thống."
            )

        # 3. LLM generation for general queries
        docs_summary = ""
        if indexed_docs:
            if lang == "en":
                docs_summary = "\nCurrent documents in knowledge base:\n" + "\n".join(
                    f"- {d['file_name']} ({d['chunk_count']} vector chunks)" for d in indexed_docs
                )
            else:
                docs_summary = "\nCác tài liệu hiện có trong kho tri thức:\n" + "\n".join(
                    f"- {d['file_name']} ({d['chunk_count']} đoạn véc-tơ)" for d in indexed_docs
                )
        else:
            docs_summary = "\nThe knowledge base is currently empty." if lang == "en" else "\nHiện tại kho tri thức chưa có tài liệu nào."

        if self.llm_provider:
            try:
                clean_history = []
                if chat_history:
                    for h in chat_history[-3:]:
                        c = h.get("content", "")
                        c_clean = re.sub(r"(?i)lễ tân kiêm điều phối viên", "trợ lý HedgeDoc", c)
                        c_clean = re.sub(r"(?i)lễ tân", "trợ lý HedgeDoc", c_clean)
                        clean_history.append({"role": h.get("role", "user"), "content": c_clean})

                if lang == "en":
                    prompt = (
                        f"CURRENT KNOWLEDGE BASE:\n{docs_summary}\n\n"
                        f"RECENT CHAT HISTORY: {clean_history if clean_history else 'Session start'}\n\n"
                        f"USER QUERY: {query}\n\n"
                        f"REQUIREMENT: Answer concisely and directly in ENGLISH. Absolutely do not roleplay as a receptionist or cashier:"
                    )
                    sys_prompt = FRONTDESK_SYSTEM_PROMPT_EN
                else:
                    prompt = (
                        f"THÔNG TIN HỆ THỐNG HIỆN TẠI:\n{docs_summary}\n\n"
                        f"LỊCH SỬ TRAO ĐỔI GẦN ĐÂY: {clean_history if clean_history else 'Bắt đầu phiên'}\n\n"
                        f"CÂU HỎI CỦA NGƯỜI DÙNG: {query}\n\n"
                        f"YÊU CẦU: Trả lời ngắn gọn, đúng trọng tâm câu hỏi. TUYỆT ĐỐI KHÔNG tự xưng là lễ tân hay điều phối viên:"
                    )
                    sys_prompt = FRONTDESK_SYSTEM_PROMPT_VI

                answer = self.llm_provider.generate(
                    prompt=prompt,
                    system_prompt=sys_prompt
                )
                if answer and answer.strip():
                    cleaned = re.sub(r"(?i)lễ tân kiêm điều phối viên", "HedgeDoc", answer)
                    cleaned = re.sub(r"(?i)lễ tân", "HedgeDoc", cleaned)
                    return cleaned.strip()
            except Exception:
                pass

        # Fallback response
        if lang == "en":
            return (
                "I am **HedgeDoc**, ready to assist you with document intelligence.\n\n"
                f"{docs_summary}\n\n"
                "Please enter your inquiry or upload new documents on the left sidebar."
            )
        return (
            "Tôi là **HedgeDoc**, sẵn sàng hỗ trợ bạn tra cứu tri thức tài liệu.\n\n"
            f"{docs_summary}\n\n"
            "Vui lòng nhập câu hỏi cần tra cứu hoặc nạp thêm tài liệu ở thanh bên trái."
        )

    def respond_not_found(
        self,
        query: str,
        indexed_docs: List[Dict[str, Any]],
        matched_doc: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Informs the user concisely that the knowledge base lacks information for this query,
        in the query's language (EN / VI). Offers helpful follow-up directions if a document is matched.
        """
        lang = detect_language(query)
        if matched_doc:
            title = clean_doc_title(matched_doc.get("file_name", ""))
            if lang == "en":
                return (
                    f"In **{title}**, detailed information regarding **\"{query}\"** was not found.\n\n"
                    "However, this document covers several prominent areas. Would you like to explore one of the suggested topics below?"
                )
            return (
                f"Trong cuốn sách/tài liệu **{title}**, chưa tìm thấy nội dung chi tiết về: **\"{query}\"**.\n\n"
                "Tuy nhiên, tài liệu này có các phần nội dung nổi bật đáng chú ý. Bạn có thể chọn tìm hiểu về một trong các chủ đề gợi ý bên dưới:"
            )

        if lang == "en":
            if indexed_docs:
                doc_list = "\n".join(f"- **{clean_doc_title(d['file_name'])}**" for d in indexed_docs[:3])
                return (
                    f"I need a bit more specific context to answer **\"{query}\"** accurately.\n\n"
                    f"Currently available documents in the knowledge base:\n{doc_list}\n\n"
                    "Which document would you like to query, or could you provide more specific keywords or select one of the suggested topics below?"
                )
            return (
                f"No information was found regarding: **\"{query}\"** because the knowledge base is currently empty.\n\n"
                "**Tip:** You can upload relevant documents on the left sidebar and click **\"Nạp vào kho tri thức\"**."
            )

        if indexed_docs:
            doc_list = "\n".join(f"- **{clean_doc_title(d['file_name'])}**" for d in indexed_docs[:3])
            return (
                f"Hệ thống cần thêm thông tin cụ thể để tra cứu chính xác cho câu hỏi: **\"{query}\"**.\n\n"
                f"Các tài liệu hiện có trong kho tri thức:\n{doc_list}\n\n"
                "Bạn đang muốn tra cứu nội dung này trong tài liệu nào, hoặc bạn có thể chọn một trong các chủ đề gợi ý bên dưới?"
            )
        return (
            f"Trong kho tri thức hiện tại chưa có tài liệu nào để tra cứu câu hỏi: **\"{query}\"**.\n\n"
            "**Gợi ý:** Bạn có thể tải tài liệu liên quan ở thanh bên trái và bấm **\"Nạp vào kho tri thức\"**."
        )
