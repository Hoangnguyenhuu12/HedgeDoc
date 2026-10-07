"""
Multi-Agent Coordinator for HedgeDoc.
Coordinates FrontdeskAgent and ResearchAgent into a unified, collaborative workflow.
"""

from typing import Any, Dict, List, Optional
from .frontdesk_agent import FrontdeskAgent
from .research_agent import ResearchAgent
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
        intent = self.frontdesk_agent.classify_intent(query)

        # ----------------------------------------------------------------------
        # SCENARIO 1: Greeting, General System Info, or Workflow Guidance
        # ----------------------------------------------------------------------
        if intent == "frontdesk_chat":
            thought = (
                "[Tác tử Lễ tân]: Nhận diện câu chào hỏi / hỏi thông tin sử dụng hệ thống.\n"
                "-> Trả lời trực tiếp người dùng, hướng dẫn các tính năng của HedgeDoc và liệt kê tài liệu trong kho."
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
                "agent_route": "frontdesk_direct"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 2: Document Research & Fact Extraction
        # ----------------------------------------------------------------------
        thought_steps = [
            "[Tác tử Lễ tân]: Phân tích câu hỏi cần tra cứu kiến thức thực tế từ tài liệu.",
            "[Tác tử Lễ tân -> Tác tử Chuyên gia]: Chuyển giao yêu cầu tra cứu sang Chuyên gia Nghiên cứu Tài liệu...",
        ]

        research_res = self.research_agent.research(
            query=query,
            top_k=top_k,
            chat_history=chat_history
        )

        if research_res.get("found"):
            thought_steps.append(
                f"[Tác tử Chuyên gia Nghiên cứu]: Đã tìm thấy {len(research_res.get('citations', []))} đoạn trích dẫn và tổng hợp câu trả lời căn cứ từ tài liệu."
            )
            return {
                "answer": research_res.get("answer"),
                "thought": "\n".join(thought_steps),
                "citations": research_res.get("citations", []),
                "agent_route": "research_specialist"
            }
        else:
            thought_steps.append(
                "[Tác tử Chuyên gia Nghiên cứu]: Không tìm thấy đủ cơ sở dữ liệu trong các tài liệu hiện có."
            )
            thought_steps.append(
                "[Tác tử Lễ tân]: Tiếp nhận và giải thích lịch sự, hướng dẫn người dùng tải thêm tệp tài liệu vào kho."
            )
            friendly_answer = self.frontdesk_agent.respond_not_found(
                query=query,
                indexed_docs=indexed_docs
            )
            return {
                "answer": friendly_answer,
                "thought": "\n".join(thought_steps),
                "citations": research_res.get("citations", []),
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
            Dict containing thought, citations, stream (generator), and agent_route.
        """
        indexed_docs = indexed_docs or self.rag_client.list_indexed_documents()
        intent = self.frontdesk_agent.classify_intent(query)

        def _word_stream(text: str):
            words = text.split(" ")
            for idx, w in enumerate(words):
                yield w + (" " if idx < len(words) - 1 else "")

        # ----------------------------------------------------------------------
        # SCENARIO 1: Greeting, General System Info, or Workflow Guidance
        # ----------------------------------------------------------------------
        if intent == "frontdesk_chat":
            thought = (
                "[Tác tử Lễ tân]: Nhận diện câu chào hỏi / hỏi thông tin sử dụng hệ thống.\n"
                "-> Trả lời trực tiếp người dùng, hướng dẫn các tính năng của HedgeDoc và liệt kê tài liệu trong kho."
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
                "agent_route": "frontdesk_direct"
            }

        # ----------------------------------------------------------------------
        # SCENARIO 2: Document Research & Fact Extraction
        # ----------------------------------------------------------------------
        thought_steps = [
            "[Tác tử Lễ tân]: Phân tích câu hỏi cần tra cứu kiến thức thực tế từ tài liệu.",
            "[Tác tử Lễ tân -> Tác tử Chuyên gia]: Chuyển giao yêu cầu tra cứu sang Chuyên gia Nghiên cứu Tài liệu...",
        ]

        research_res = self.research_agent.stream_research(
            query=query,
            top_k=top_k,
            chat_history=chat_history
        )

        if research_res.get("found"):
            citations = research_res.get("citations", [])
            thought_steps.append(
                f"[Tác tử Chuyên gia Nghiên cứu]: Đã tìm thấy {len(citations)} đoạn trích dẫn và truyền dữ liệu thời gian thực căn cứ từ tài liệu."
            )
            return {
                "thought": "\n".join(thought_steps),
                "citations": citations,
                "stream": research_res.get("stream"),
                "agent_route": "research_specialist"
            }
        else:
            thought_steps.append(
                "[Tác tử Chuyên gia Nghiên cứu]: Không tìm thấy đủ cơ sở dữ liệu trong các tài liệu hiện có."
            )
            thought_steps.append(
                "[Tác tử Lễ tân]: Tiếp nhận và giải thích lịch sự, hướng dẫn người dùng tải thêm tệp tài liệu vào kho."
            )
            friendly_answer = self.frontdesk_agent.respond_not_found(
                query=query,
                indexed_docs=indexed_docs
            )
            return {
                "thought": "\n".join(thought_steps),
                "citations": research_res.get("citations", []),
                "stream": _word_stream(friendly_answer),
                "agent_route": "frontdesk_guidance"
            }

