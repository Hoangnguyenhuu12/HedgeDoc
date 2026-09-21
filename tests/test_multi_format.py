"""
Test suite for Multi-Format Document Ingestion & Strict RAG Queries (Word .docx & Excel .xlsx).
"""

import sys
import io
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from data_layer.loader import MultiFormatDocumentLoader
from backend.rag_engine import RAGEngine

def test_multiformat_pipeline():
    print("=" * 70)
    print("TESTING MULTI-FORMAT DOCUMENT PIPELINE (WORD & EXCEL)")
    print("=" * 70)

    loader = MultiFormatDocumentLoader()
    engine = RAGEngine()

    docx_path = config.RAW_DOCS_DIR / "chinh_sach_nhan_su_va_van_hanh_2025.docx"
    excel_path = config.RAW_DOCS_DIR / "bao_cao_kinh_doanh_2025.xlsx"

    # 1. Test DOCX extraction
    print("\n[TEST 1] Testing Word (.docx) Extraction...")
    docx_pages = loader.load_document(docx_path)
    print(f"  - Extracted {len(docx_pages)} sections from {docx_path.name}")
    assert len(docx_pages) >= 5, "Word document sections count too low!"
    for p in docx_pages[:3]:
        print(f"    + {p.location_label} (Chars: {len(p.text)})")

    # 2. Test Excel extraction
    print("\n[TEST 2] Testing Excel (.xlsx) Extraction...")
    excel_pages = loader.load_document(excel_path)
    print(f"  - Extracted {len(excel_pages)} blocks from {excel_path.name}")
    assert len(excel_pages) >= 4, "Excel sheets count too low!"
    for p in excel_pages[:3]:
        print(f"    + {p.location_label} (Chars: {len(p.text)})")

    # 3. Test Indexing into ChromaDB
    print("\n[TEST 3] Testing Indexing into ChromaDB...")
    docx_res = engine.index_document(docx_path, force_reindex=True)
    print(f"  - Indexing DOCX: {docx_res['status']} ({docx_res.get('chunk_count', 0)} chunks)")
    assert docx_res["status"] == "success", f"DOCX indexing failed: {docx_res}"

    excel_res = engine.index_document(excel_path, force_reindex=True)
    print(f"  - Indexing XLSX: {excel_res['status']} ({excel_res.get('chunk_count', 0)} chunks)")
    assert excel_res["status"] == "success", f"XLSX indexing failed: {excel_res}"

    # 4. Test RAG Query on Excel Data
    print("\n[TEST 4] Querying Excel Data...")
    q_excel = "Doanh thu quý 3 của mảng Tu_Van_AI năm 2025 là bao nhiêu tỷ VND và tỷ suất lợi nhuận đạt bao nhiêu?"
    print(f"  - Query: '{q_excel}'")
    res_excel = engine.query(question=q_excel, top_k=6, doc_id_filter=excel_res["doc_id"], stream=False)
    print(f"  - Response:\n{res_excel['answer']}")
    print("  - Citations:")
    for cit in res_excel["citations"]:
        print(f"    * {cit['file_name']} - {cit.get('location_label')} (Dist: {cit['distance']:.4f})")
    assert len(res_excel["citations"]) > 0, "No citations returned for Excel query!"
    assert "56.2" in res_excel["answer"] or "56,2" in res_excel["answer"], "Failed to extract exact revenue from Excel table!"

    # 5. Test RAG Query on Word Data
    print("\n[TEST 5] Querying Word Document Data...")
    q_docx = "Nhân viên chính thức được nghỉ phép năm bao nhiêu ngày và được làm việc từ xa WFH tối đa mấy ngày một tuần?"
    print(f"  - Query: '{q_docx}'")
    res_docx = engine.query(question=q_docx, top_k=4, doc_id_filter=docx_res["doc_id"], stream=False)
    print(f"  - Response:\n{res_docx['answer']}")
    print("  - Citations:")
    for cit in res_docx["citations"]:
        print(f"    * {cit['file_name']} - {cit.get('location_label')} (Dist: {cit['distance']:.4f})")
    assert len(res_docx["citations"]) > 0, "No citations returned for Word query!"
    assert "12" in res_docx["answer"] and ("2" in res_docx["answer"] or "02" in res_docx["answer"]), "Failed to extract correct policy details from Word!"

    print("\n" + "=" * 70)
    print("ALL MULTI-FORMAT TESTS PASSED FLAWLESSLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_multiformat_pipeline()
