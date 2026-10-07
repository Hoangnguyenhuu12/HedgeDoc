"""
Integration tests for DocumentPipelineOrchestrator in HedgeDoc.
"""

from pathlib import Path
import pytest
import pymupdf as fitz

from HedgeDoc.workflows.document_pipeline import DocumentPipelineOrchestrator


@pytest.fixture
def clean_pdf(tmp_path) -> Path:
    pdf_path = tmp_path / "orchestrator_doc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Add substantial text lines across the page for realistic document contrast and edge distribution
    page.insert_text(fitz.Point(50, 70), "HedgeDoc High Quality End to End Pipeline Verification Document", fontsize=14)
    y = 120
    for i in range(15):
        page.insert_text(fitz.Point(50, y), f"Section {i+1}: Standard operating procedures and architectural decoupling validation.", fontsize=11)
        y += 35
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_orchestrator_full_pipeline(clean_pdf):
    orchestrator = DocumentPipelineOrchestrator()
    logs = []

    def on_prog(msg, pct):
        logs.append((msg, pct))

    result = orchestrator.process_document(clean_pdf, progress_callback=on_prog)

    assert result["status"] == "success"
    assert result["file_name"] == clean_pdf.name
    assert "quality_assessment" in result
    assert result["quality_assessment"]["recommendation"] in ["direct_to_ocr", "enhance_before_ocr"]
    assert "ocr_summary" in result
    assert result["ocr_summary"]["total_pages"] >= 1
    assert "rag_indexing" in result
    assert len(logs) >= 3

    # Test query through orchestrator
    q_res = orchestrator.query("Pipeline Verification")
    assert "answer" in q_res


def test_orchestrator_streaming_query(clean_pdf):
    orchestrator = DocumentPipelineOrchestrator()
    orchestrator.process_document(clean_pdf)

    # 1. Test frontdesk streaming response
    greeting_stream = orchestrator.stream_query("Xin chào")
    assert "thought" in greeting_stream
    assert greeting_stream["agent_route"] == "frontdesk_direct"
    tokens = list(greeting_stream["stream"])
    assert len(tokens) > 0

    # 2. Test document research streaming response
    research_stream = orchestrator.stream_query("Pipeline Verification")
    assert "thought" in research_stream
    assert "citations" in research_stream
    if research_stream.get("stream"):
        res_tokens = list(research_stream["stream"])
        assert len(res_tokens) > 0

