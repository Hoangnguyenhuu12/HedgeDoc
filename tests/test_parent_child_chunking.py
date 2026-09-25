"""
Test suite for Structure-Aware Parent-Child Chunking (Principle 8).
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_layer.loader import ExtractedPage
from data_layer.chunker import DocumentChunker, DocumentChunk


class TestParentChildChunking(unittest.TestCase):
    def setUp(self):
        self.chunker = DocumentChunker(chunk_size=500, child_size=200)

    def test_article_struct_path_and_parent_child(self):
        legal_text = (
            "Điều 1. Phạm vi điều chỉnh\n"
            "Quy chế này quy định chế độ làm việc và bảo mật thông tin nội bộ của công ty.\n\n"
            "Điều 2. Thời gian làm việc\n"
            "Thời gian làm việc tiêu chuẩn là 8 giờ mỗi ngày từ thứ Hai đến thứ Sáu hàng tuần. "
            "Cán bộ nhân viên làm thêm giờ vào ngày nghỉ được hưởng lương làm thêm giờ theo quy định của Bộ luật Lao động."
        )
        page = ExtractedPage(
            page_number=1,
            total_pages=1,
            text=legal_text,
            doc_id="legal_doc_01",
            file_name="quy_che_2025.docx",
            location_label="Mục 1"
        )

        chunks = self.chunker.chunk_page(page)
        self.assertGreater(len(chunks), 1)

        # Check struct_paths
        paths = [c.struct_path for c in chunks]
        self.assertTrue(any("Điều 1" in p for p in paths))
        self.assertTrue(any("Điều 2" in p for p in paths))

        # Check that child chunks have parent_id and parent_text
        for c in chunks:
            self.assertIsNotNone(c.parent_id)
            self.assertIn("parent_text", c.metadata)
            self.assertGreater(len(c.metadata["parent_text"]), len(c.text) - 1)

    def test_table_preservation_as_single_parent(self):
        table_text = (
            "| Quy | Doanh_Thu | Loi_Nhuan |\n"
            "| Q1 | 120 | 35 |\n"
            "| Q2 | 150 | 45 |\n"
            "| Q3 | 180 | 55 |\n"
            "| Q4 | 210 | 70 |"
        )
        page = ExtractedPage(
            page_number=1,
            total_pages=1,
            text=table_text,
            doc_id="report_xlsx",
            file_name="bao_cao_2025.xlsx",
            location_label="Sheet 'Báo cáo Q1-Q4'"
        )

        chunks = self.chunker.chunk_page(page)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, table_text)
        self.assertEqual(chunks[0].metadata["is_child"], False)


if __name__ == "__main__":
    unittest.main()
