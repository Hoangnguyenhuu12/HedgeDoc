"""
Frontdesk Agent (Receptionist & User Guide).
Handles conversational greetings, onboarding, user instructions,
and coordinates with specialized downstream agents.
"""

from typing import Any, Dict, List, Optional
import re


FRONTDESK_SYSTEM_PROMPT = """\
Bạn là Lễ tân kiêm Điều phối viên của HedgeDoc — Nền tảng Quản lý và Khai phá Tri thức Tài liệu.
Vai trò của bạn giống như một nhân viên lễ tân hoặc thu ngân chuyên nghiệp, chu đáo và am hiểu mọi ngóc ngách của hệ thống.

NHIỆM VỤ CHÍNH:
1. Chào đón người dùng thân thiện, lịch sự khi họ chào hỏi (như "hi", "xin chào", "hello").
2. Giới thiệu bản thân và các năng lực của HedgeDoc khi được hỏi:
   - Giúp kiểm định chất lượng tài liệu (độ nét, tương phản, độ phân giải) trước khi bóc tách.
   - Trích xuất văn bản số và cấu trúc bảng biểu, hình ảnh, chữ ký.
   - Tra cứu câu hỏi bằng ngôn ngữ tự nhiên từ kho tài liệu đã nạp.
3. Hướng dẫn người dùng thao tác:
   - Tải tài liệu lên ở thanh bên trái (hỗ trợ PDF, Word, Excel, ảnh scan).
   - Nhấn "Nạp vào kho tri thức" để hệ thống phân đoạn và lập chỉ mục véc-tơ.
   - Nhập câu hỏi vào khung chat bên dưới để tra cứu chi tiết.
   - Quản lý, xóa tài liệu trong mục "Kho tri thức đã lưu".
4. Nếu người dùng hỏi về tài liệu hiện có: Liệt kê danh sách các tài liệu đang có trong kho tri thức một cách rõ ràng.

PHONG CÁCH GIAO TIẾP:
- Nhã nhặn, nhiệt tình, lịch sự và súc tích.
- Trình bày định dạng Markdown rõ ràng, dễ đọc.
"""


class FrontdeskAgent:
    """Receptionist agent handling conversation and system orientation."""

    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    def classify_intent(self, query: str) -> str:
        """
        Classifies whether user query is a general/social question or a document research query.
        Returns:
            "frontdesk_chat": Greeting, system inquiry, capabilities, or file operations.
            "document_research": Query requiring factual retrieval from ingested documents.
        """
        q = query.strip().lower()

        # Common greeting patterns
        greetings = [
            r"^(hi|hello|helo|hey|chào|xin chào|halo|alo)\b",
            r"^(bạn là ai|bạn tên gì|bạn có thể làm gì|bạn giúp được gì)\b",
            r"^(hướng dẫn|cách dùng|làm sao để|cách nạp|thêm file|tải file)\b",
            r"^(trong kho có gì|có những sách nào|danh sách tài liệu|tài liệu nào)\b",
            r"^(cảm ơn|thank you|thanks|tạm biệt|bye)\b"
        ]

        for pattern in greetings:
            if re.search(pattern, q):
                return "frontdesk_chat"

        # If very short query with no context (<= 2 words) like "ai đó", "alo"
        words = q.split()
        if len(words) <= 2 and any(w in ("hi", "hello", "chào", "alo", "helo") for w in words):
            return "frontdesk_chat"

        return "document_research"

    def respond_conversational(
        self,
        query: str,
        indexed_docs: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generates a warm, informative response from the Frontdesk Agent.
        """
        docs_summary = ""
        if indexed_docs:
            docs_summary = "\nCác tài liệu hiện có trong kho tri thức:\n" + "\n".join(
                f"- {d['file_name']} ({d['chunk_count']} đoạn véc-tơ)" for d in indexed_docs
            )
        else:
            docs_summary = "\nHiện tại kho tri thức chưa có tài liệu nào."

        prompt = (
            f"THÔNG TIN HỆ THỐNG HIỆN TẠI:\n{docs_summary}\n\n"
            f"LỊCH SỬ TRAO ĐỔI GẦN ĐÂY: {chat_history[-3:] if chat_history else 'Bắt đầu phiên'}\n\n"
            f"CÂU HỎI CỦA NGƯỜI DÙNG: {query}\n\n"
            f"HÃY ĐÓNG VAI LỄ TÂN HEDGEDOC TRẢ LỜI NGƯỜI DÙNG THẬT LỊCH SỰ, RÕ RÀNG VÀ HỮU ÍCH:"
        )

        if self.llm_provider:
            try:
                answer = self.llm_provider.generate(
                    prompt=prompt,
                    system_prompt=FRONTDESK_SYSTEM_PROMPT
                )
                if answer and answer.strip():
                    return answer.strip()
            except Exception:
                pass

        # Fallback response if LLM is unavailable
        if any(w in query.lower() for w in ("hi", "hello", "chào")):
            return (
                "Xin chào bạn! Tôi là trợ lý ảo **HedgeDoc**.\n\n"
                "Tôi có thể hỗ trợ bạn kiểm định chất lượng, bóc tách nội dung và tra cứu thông tin chuyên sâu từ các tài liệu số hoặc tài liệu quét.\n\n"
                f"{docs_summary}\n\n"
                "Bạn có thể đặt câu hỏi về các tài liệu trên hoặc tải thêm tài liệu mới ở thanh bên trái nhé!"
            )
        return (
            "Tôi là **HedgeDoc**, trợ lý khai thác tri thức tài liệu.\n\n"
            f"{docs_summary}\n\n"
            "Bạn hãy nhập câu hỏi cần tra cứu hoặc tải lên tệp tài liệu mới ở thanh bên để tôi hỗ trợ nhé!"
        )

    def respond_not_found(
        self,
        query: str,
        indexed_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Politely informs the user that the knowledge base lacks information for this query
        and offers guidance on how to supplement with new documents.
        """
        doc_names = ", ".join(f"*{d['file_name']}*" for d in indexed_docs) if indexed_docs else "chưa có tài liệu nào"
        return (
            f"Hiện tại trong kho tri thức (gồm: {doc_names}), các tài liệu chưa đề cập đến nội dung câu hỏi: **\"{query}\"**.\n\n"
            "💡 **Gợi ý dành cho bạn:**\n"
            "- Bạn có thể tải thêm tệp tài liệu hoặc tài liệu chứa thông tin này ở thanh điều khiển bên trái rồi bấm **\"Nạp vào kho tri thức\"**.\n"
            "- Hoặc thử diễn đạt lại câu hỏi theo các từ khóa cụ thể hơn có trong sách/tài liệu."
        )
