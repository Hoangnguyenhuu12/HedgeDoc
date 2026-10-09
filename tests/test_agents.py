"""
Unit and integration tests for HedgeDoc Multi-Agent Collaborative System.
Tests FrontdeskAgent, MultiAgentCoordinator, and Language Mirroring / Context Memory.
"""

import pytest
from typing import Dict, Any, List

from HedgeDoc.agents.frontdesk_agent import FrontdeskAgent
from HedgeDoc.agents.coordinator import MultiAgentCoordinator
from HedgeDoc.agents.language_utils import (
    detect_language,
    is_summarization_query,
    is_legal_inquiry,
    is_legal_document,
    is_clarification_context,
    resolve_document_from_context,
    clean_doc_title
)


@pytest.fixture
def sample_indexed_docs() -> List[Dict[str, Any]]:
    return [
        {"file_name": "Ca phe cung Tony.pdf", "chunk_count": 38},
        {"file_name": "Hoang Tu Be.pdf", "chunk_count": 15},
        {"file_name": "Khao sat thi truong 2026.docx", "chunk_count": 22}
    ]


class TestFrontdeskAgent:
    """Test suite for FrontdeskAgent intent classification and guidance."""

    def test_classify_intent_greetings(self):
        agent = FrontdeskAgent()
        assert agent.classify_intent("Xin chào bạn") == "frontdesk_chat"
        assert agent.classify_intent("Hello there!") == "frontdesk_chat"
        assert agent.classify_intent("Bạn là ai và có thể làm gì?") == "frontdesk_chat"
        assert agent.classify_intent("Who are you?") == "frontdesk_chat"
        assert agent.classify_intent("Hướng dẫn cách sử dụng hệ thống") == "frontdesk_chat"
        assert agent.classify_intent("How do I upload documents?") == "frontdesk_chat"

    def test_classify_intent_platform_capabilities(self):
        agent = FrontdeskAgent()
        assert agent.classify_intent("Kiểm định chất lượng tài liệu scan") == "platform_capabilities"
        assert agent.classify_intent("Hệ thống đo độ nét và độ tương phản thế nào?") == "platform_capabilities"
        assert agent.classify_intent("Tiêu chuẩn OCR readiness là gì?") == "platform_capabilities"
        assert agent.classify_intent("Explain document quality gate and sharpness metrics") == "platform_capabilities"

    def test_classify_intent_document_summary(self):
        agent = FrontdeskAgent()
        assert agent.classify_intent("Tóm tắt nội dung tài liệu") == "document_summary"
        assert agent.classify_intent("Tóm tắt cuốn Cà phê cùng Tony") == "document_summary"
        assert agent.classify_intent("Tổng quan nội dung chính cuốn sách này") == "document_summary"
        assert agent.classify_intent("Summarize this document") == "document_summary"
        assert agent.classify_intent("What is the Little Prince about?") == "document_summary"

    def test_classify_intent_document_research(self):
        agent = FrontdeskAgent()
        assert agent.classify_intent("Tony khuyên học tiếng Anh như thế nào?") == "document_research"
        assert agent.classify_intent("Hoàng tử bé đã gặp những ai trên các tiểu tinh cầu?") == "document_research"
        assert agent.classify_intent("What is the fox's secret in chapter 21?") == "document_research"

    def test_respond_not_found_with_matched_doc(self, sample_indexed_docs):
        agent = FrontdeskAgent()
        matched = sample_indexed_docs[0]
        # Vietnamese
        resp_vi = agent.respond_not_found("đầu tư bất động sản", sample_indexed_docs, matched_doc=matched)
        assert clean_doc_title(matched["file_name"]) in resp_vi
        assert "đầu tư bất động sản" in resp_vi
        assert "chủ đề gợi ý" in resp_vi

        # English
        resp_en = agent.respond_not_found("What is the cryptocurrency investment strategy?", sample_indexed_docs, matched_doc=matched)
        assert clean_doc_title(matched["file_name"]) in resp_en
        assert "cryptocurrency investment strategy" in resp_en

    def test_respond_not_found_empty_kb(self):
        agent = FrontdeskAgent()
        # Vietnamese empty
        resp_vi = agent.respond_not_found("tỷ giá hối đoái", indexed_docs=[], matched_doc=None)
        assert "chưa có tài liệu nào" in resp_vi

        # English empty
        resp_en = agent.respond_not_found("What are the current exchange rates?", indexed_docs=[], matched_doc=None)
        assert "currently empty" in resp_en

    def test_respond_not_found_with_doc_list(self, sample_indexed_docs):
        agent = FrontdeskAgent()
        resp = agent.respond_not_found("công thức hóa học", sample_indexed_docs, matched_doc=None)
        assert "Hệ thống cần thêm thông tin cụ thể" in resp
        assert "Ca phe cung Tony" in resp


class TestMultiAgentCoordinator:
    """Test suite for MultiAgentCoordinator routing, catalog suggestions, and multi-turn memory."""

    def test_catalog_suggestions(self, sample_indexed_docs):
        coord = MultiAgentCoordinator()
        # Vietnamese suggestions
        sug_vi = coord._get_catalog_suggestions(sample_indexed_docs, lang="vi")
        assert len(sug_vi) == 3
        assert any("Tóm tắt" in s for s in sug_vi)

        # English suggestions
        sug_en = coord._get_catalog_suggestions(sample_indexed_docs, lang="en")
        assert len(sug_en) == 3
        assert any("Summarize" in s for s in sug_en)

        # Empty knowledge base suggestions
        empty_sug_vi = coord._get_catalog_suggestions([], lang="vi")
        assert len(empty_sug_vi) >= 1
        assert "Hướng dẫn nạp tài liệu" in empty_sug_vi

    def test_non_legal_guidance_for_literary_books(self, sample_indexed_docs):
        coord = MultiAgentCoordinator()
        # All 3 sample docs are non-legal
        res = coord.process("Tra cứu quy định & điều khoản chính", indexed_docs=sample_indexed_docs)
        assert res["agent_route"] == "non_legal_guidance"
        assert "không có các điều khoản pháp lý hoặc quy định bắt buộc" in res["answer"]
        assert len(res["suggested_followups"]) == 3
        assert "Các nguyên tắc sống và bài học ứng xử" in res["suggested_followups"]

    def test_multi_turn_clarification_resolution(self, sample_indexed_docs):
        coord = MultiAgentCoordinator()
        chat_history = [
            {"role": "user", "content": "Tóm tắt nội dung tài liệu"},
            {
                "role": "assistant",
                "content": (
                    "Hiện tại trong kho tri thức đang có các tài liệu sau:\n\n"
                    "1. **Ca Phe Cung Tony** (38 đoạn véc-tơ)\n"
                    "2. **Hoang Tu Be** (15 đoạn véc-tơ)\n\n"
                    "Bạn muốn tôi tóm tắt cuốn sách hay tài liệu nào trong số trên? Vui lòng chọn bên dưới hoặc cho tôi biết tên tác phẩm bạn quan tâm."
                )
            }
        ]

        # Verify clarification detector
        assert is_clarification_context(chat_history) is True

        # Test resolving ordinal 'cuốn thứ nhất'
        target_first = resolve_document_from_context("cuốn thứ nhất", chat_history, sample_indexed_docs)
        assert target_first is not None
        assert target_first["file_name"] == "Ca phe cung Tony.pdf"

        # Test resolving ordinal 'cuốn 2'
        target_second = resolve_document_from_context("cuốn 2", chat_history, sample_indexed_docs)
        assert target_second is not None
        assert target_second["file_name"] == "Hoang Tu Be.pdf"

        # Test resolving short keyword 'Tony'
        target_tony = resolve_document_from_context("Tony", chat_history, sample_indexed_docs)
        assert target_tony is not None
        assert target_tony["file_name"] == "Ca phe cung Tony.pdf"

        # Test resolving short keyword 'Hoàng tử bé'
        target_prince = resolve_document_from_context("Hoàng tử bé", chat_history, sample_indexed_docs)
        assert target_prince is not None
        assert target_prince["file_name"] == "Hoang Tu Be.pdf"


class TestLanguageAndLegalUtils:
    """Test suite for language_utils helpers."""

    def test_detect_language(self):
        assert detect_language("Xin chào HedgeDoc, bạn có thể giúp tôi được không?") == "vi"
        assert detect_language("Hello HedgeDoc, can you summarize this document for me?") == "en"

    def test_is_legal_inquiry(self):
        assert is_legal_inquiry("Tra cứu quy định & điều khoản chính") is True
        assert is_legal_inquiry("Quy định về thời hạn thanh toán trong hợp đồng") is True
        assert is_legal_inquiry("What are the terms and conditions?") is True
        assert is_legal_inquiry("Tóm tắt tác phẩm Hoàng tử bé") is False

    def test_is_legal_document(self):
        assert is_legal_document("Hop_dong_kinh_te_2026.pdf") is True
        assert is_legal_document("Thong_tu_15_quy_dinh_tai_chinh.pdf") is True
        assert is_legal_document("terms_and_conditions.docx") is True
        assert is_legal_document("Ca phe cung Tony.pdf") is False
        assert is_legal_document("Hoang Tu Be.pdf") is False

    def test_clean_doc_title(self):
        assert clean_doc_title("10048-Ca-phe-cung-Tony-thuviensach.vn.pdf") == "Ca phe cung Tony"
        assert clean_doc_title("Hoang_Tu_Be_doc.pdf") == "Hoang Tu Be"
