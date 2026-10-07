"""
Document Pipeline Orchestrator.
Orchestrates the complete modular Document AI flow:
1. Document Quality Gate (Assess readiness, detect blur/contrast/resolution/shadow)
2. Quality Routing Decision (Reject vs Enhance vs Direct OCR)
3. OCR Engine (Extract structured markdown, blocks, tables)
4. RAG Engine (Parent-child chunking, ChromaDB vector indexing)
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import pymupdf as fitz

from HedgeDoc.services.quality_gate_client import QualityGateClient
from HedgeDoc.services.ocr_client import OCRClient
from HedgeDoc.services.rag_client import RAGClient
from HedgeDoc.agents.coordinator import MultiAgentCoordinator


class DocumentPipelineOrchestrator:
    """
    Coordinates Quality Gate, OCR Engine, RAG Engine, and Multi-Agent Collaborative System.
    """

    def __init__(
        self,
        quality_client: Optional[QualityGateClient] = None,
        ocr_client: Optional[OCRClient] = None,
        rag_client: Optional[RAGClient] = None,
        coordinator: Optional[MultiAgentCoordinator] = None,
    ):
        self.quality_client = quality_client or QualityGateClient()
        self.ocr_client = ocr_client or OCRClient()
        self.rag_client = rag_client or RAGClient()
        self.coordinator = coordinator or MultiAgentCoordinator(rag_client=self.rag_client)

    def process_document(
        self,
        file_path: Path,
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end ingestion pipeline:
        File -> Quality Gate -> Decision -> OCR Engine -> RAG Indexing.
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            return {
                "status": "error",
                "message": f"Tệp không tồn tại: {file_path}",
                "file_name": file_path.name
            }

        # ----------------------------------------------------------------------
        # STEP 1: AI DOCUMENT QUALITY GATE
        # ----------------------------------------------------------------------
        if progress_callback:
            progress_callback("Đang kiểm định chất lượng tài liệu qua Quality Gate...", 0.2)

        try:
            assessment = self.quality_client.assess_document(file_path)
        except Exception as exc:
            assessment = {
                "overall_quality": 3.0,
                "ocr_readiness": "medium",
                "detected_issues": [f"Lỗi kiểm định: {str(exc)}"],
                "recommendation": "direct_to_ocr"
            }

        recommendation = assessment.get("recommendation", "direct_to_ocr")

        # Check if file has a native digital text layer (non-scanned or hybrid document)
        has_digital_text = False
        total_digital_chars = 0
        total_pages_count = 1
        if file_path.suffix.lower() == ".pdf":
            try:
                chk_doc = fitz.open(file_path)
                total_pages_count = len(chk_doc)
                total_digital_chars = sum(len(chk_doc[i].get_text("text").strip()) for i in range(total_pages_count))
                chk_doc.close()
                if total_digital_chars >= 50:
                    has_digital_text = True
            except Exception:
                pass
        elif file_path.suffix.lower() in (".docx", ".doc", ".xlsx", ".xls"):
            has_digital_text = True
            total_digital_chars = 500

        # ----------------------------------------------------------------------
        # STEP 2: QUALITY ROUTING & EXTRACTION SELECTION
        # ----------------------------------------------------------------------
        # Case A: Scanned document rejected by Quality Gate with no digital text
        if recommendation == "reject_and_request_reupload" and not has_digital_text:
            if progress_callback:
                progress_callback("Tài liệu quét không đạt chất lượng tối thiểu và không có lớp văn bản số, bị từ chối.", 1.0)
            return {
                "status": "rejected",
                "message": "Tài liệu bị từ chối do chất lượng quét quá thấp (mờ/thiếu tương phản) và không chứa lớp văn bản kỹ thuật số.",
                "file_name": file_path.name,
                "quality_assessment": assessment,
                "ocr_summary": None,
                "rag_indexing": None
            }

        # Case B: Document has native digital text (Direct digital chunking fallback)
        if has_digital_text:
            if progress_callback:
                progress_callback("Tài liệu dạng chữ kỹ thuật số, tự động phân đoạn văn bản nguyên bản trực tiếp...", 0.6)
            try:
                rag_indexing = self.rag_client.index_document(file_path)
                chunk_count = rag_indexing.get("chunk_count", 0) if isinstance(rag_indexing, dict) else 0
                if progress_callback:
                    progress_callback("Hoàn tất nạp văn bản kỹ thuật số vào kho tri thức!", 1.0)
                return {
                    "status": "success",
                    "file_name": file_path.name,
                    "extraction_mode": "digital_text",
                    "quality_assessment": assessment,
                    "ocr_summary": {
                        "total_pages": total_pages_count,
                        "total_blocks": chunk_count,
                        "total_tables": 0,
                        "char_count": total_digital_chars,
                        "backend_used": "Văn bản số (PyMuPDF)"
                    },
                    "rag_indexing": rag_indexing
                }
            except Exception as exc:
                return {
                    "status": "error",
                    "message": f"Lỗi phân đoạn văn bản số: {str(exc)}",
                    "file_name": file_path.name,
                    "quality_assessment": assessment
                }

        # Case C: Scanned document without digital text -> Route through OCR Engine
        if progress_callback:
            msg = "Đang nhận dạng ký tự quang học qua OCR Engine..."
            if recommendation == "enhance_before_ocr":
                msg += " (Cần tăng cường chất lượng)"
            progress_callback(msg, 0.5)

        try:
            ocr_output = self.ocr_client.process_document(file_path)
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Lỗi OCR Engine: {str(exc)}",
                "file_name": file_path.name,
                "quality_assessment": assessment
            }

        # ----------------------------------------------------------------------
        # STEP 4: DOCUMENT RAG ENGINE INDEXING
        # ----------------------------------------------------------------------
        if progress_callback:
            progress_callback("Đang phân đoạn và nạp dữ liệu vào kho RAG...", 0.8)

        try:
            rag_indexing = self.rag_client.index_ocr_output(
                ocr_data=ocr_output,
                source_path=file_path.name
            )
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Lỗi RAG Engine: {str(exc)}",
                "file_name": file_path.name,
                "quality_assessment": assessment,
                "ocr_summary": {
                    "pages": len(ocr_output.get("pages", [])),
                    "blocks": len(ocr_output.get("pages", []))
                }
            }

        if progress_callback:
            progress_callback("Hoàn tất quy trình xử lý tài liệu!", 1.0)

        pages_list = ocr_output.get("pages", [])
        total_pages_ocr = ocr_output.get("total_pages", len(pages_list))
        total_tables = sum(len(p.get("tables", [])) for p in pages_list)
        total_layout = sum(len(p.get("layout_elements", [])) for p in pages_list)
        char_count = len(ocr_output.get("full_text", "")) or sum(len(p.get("text", "")) for p in pages_list)
        has_scanned = any(p.get("is_scanned") for p in pages_list)
        backend_used = "Lai (Digital + VLM OCR)" if has_scanned else "Văn bản số (PyMuPDF)"

        return {
            "status": "success",
            "file_name": file_path.name,
            "quality_assessment": assessment,
            "ocr_summary": {
                "total_pages": total_pages_ocr,
                "total_blocks": total_layout or len(pages_list),
                "total_tables": total_tables,
                "char_count": char_count,
                "backend_used": backend_used
            },
            "rag_indexing": rag_indexing
        }

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        """List distinct documents persisted in the RAG store."""
        return self.rag_client.list_indexed_documents()

    def delete_document(self, file_name: str) -> bool:
        """Delete a document from ChromaDB knowledge base."""
        return self.rag_client.delete_document(file_name)

    def clear_all_documents(self) -> bool:
        """Clear all documents from ChromaDB knowledge base."""
        return self.rag_client.clear_all_documents()

    def query(
        self,
        query_text: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes query retrieval and synthesis against the RAG knowledge base via Multi-Agent system.
        """
        return self.coordinator.process(
            query=query_text,
            top_k=top_k,
            chat_history=chat_history,
            indexed_docs=self.list_indexed_documents()
        )

    def stream_query(
        self,
        query_text: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes query retrieval and synthesis with real-time token streaming.
        """
        return self.coordinator.process_stream(
            query=query_text,
            top_k=top_k,
            chat_history=chat_history,
            indexed_docs=self.list_indexed_documents()
        )

