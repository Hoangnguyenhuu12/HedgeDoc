"""
Tests for HedgeDoc service client adapters.
"""

from pathlib import Path
import pytest
import pymupdf as fitz

from HedgeDoc.services.quality_gate_client import QualityGateClient
from HedgeDoc.services.ocr_client import OCRClient
from HedgeDoc.services.rag_client import RAGClient


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    pdf_path = tmp_path / "test_client_doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 72), "Sample HedgeDoc Multi-Engine Document", fontsize=14)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_quality_gate_client(sample_pdf):
    client = QualityGateClient()
    assessment = client.assess_document(sample_pdf)
    assert isinstance(assessment, dict)
    assert "overall_quality" in assessment
    assert "recommendation" in assessment
    assert assessment["overall_quality"] >= 1.0


def test_ocr_client(sample_pdf):
    client = OCRClient()
    result = client.process_document(sample_pdf, backend="digital")
    assert isinstance(result, dict)
    assert "pages" in result
    assert "full_text" in result
    assert "Sample HedgeDoc" in result["full_text"]


def test_rag_client(sample_pdf):
    client = RAGClient()
    # Test index file
    index_res = client.index_document(sample_pdf)
    assert isinstance(index_res, dict)
    assert index_res.get("status") in ["success", "already_indexed"]

    # Test query
    query_res = client.query("Multi-Engine Document", top_k=2)
    assert isinstance(query_res, dict)
    assert "answer" in query_res
