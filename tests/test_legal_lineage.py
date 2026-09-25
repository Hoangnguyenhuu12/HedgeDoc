"""
Test suite for Legal Lineage & Validity Warnings (Principle 9 / [INV-HEDGE-04]).
"""

import unittest
from pathlib import Path
import sys
import tempfile
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_layer.graph_store import LegalLineageStore


class TestLegalLineage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_lineage.db"
        self.store = LegalLineageStore(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_replaces_and_alert(self):
        # Doc 1: Old policy
        doc1_text = (
            "CÔNG TY ABC\n"
            "Số: 10/2023/QĐ-ABC\n"
            "QUYẾT ĐỊNH\n"
            "Về việc ban hành quy chế làm việc năm 2023."
        )
        self.store.extract_and_index_relations(
            doc_id="doc1",
            file_name="quy_che_2023.pdf",
            full_text=doc1_text
        )

        # Before replacement: no alert
        alert_before = self.store.check_validity_alert(["quy_che_2023.pdf"])
        self.assertIsNone(alert_before)

        # Doc 2: New policy replacing Doc 1
        doc2_text = (
            "CÔNG TY ABC\n"
            "Số: 15/2025/QĐ-ABC\n"
            "QUYẾT ĐỊNH\n"
            "Về việc ban hành quy chế làm việc năm 2025.\n"
            "Điều 10. Quyết định này có hiệu lực kể từ ngày ký và thay thế hoàn toàn cho Quyết định số 10/2023/QĐ-ABC."
        )
        edges = self.store.extract_and_index_relations(
            doc_id="doc2",
            file_name="quy_che_2025.pdf",
            full_text=doc2_text
        )

        self.assertGreaterEqual(len(edges), 1)
        self.assertEqual(edges[0]["relation"], "REPLACES")
        self.assertEqual(edges[0]["target"], "10/2023/QĐ-ABC")

        # After replacement: check alert on old doc
        alert_after = self.store.check_validity_alert(["quy_che_2023.pdf"])
        self.assertIsNotNone(alert_after)
        self.assertIn("CẢNH BÁO HIỆU LỰC PHÁP LÝ", alert_after)
        self.assertIn("THAY THẾ / BÃI BỎ", alert_after)
        self.assertIn("quy_che_2025.pdf", alert_after)


if __name__ == "__main__":
    unittest.main()
