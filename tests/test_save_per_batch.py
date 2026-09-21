"""
Test Suite for Save-Per-Batch and Resumable Indexing in HedgeDoc.
"""

import sys
from pathlib import Path
import unittest

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import config
from backend.rag_engine import RAGEngine
from data_layer.loader import ExtractedPage
from data_layer.chunker import DocumentChunk


class TestSavePerBatch(unittest.TestCase):

    def setUp(self):
        self.engine = RAGEngine()

    def test_save_per_batch_and_resume(self):
        print("\n--- Running TestSavePerBatch ---")
        
        # 1. Prepare sample document in raw_docs
        sample_path = config.RAW_DOCS_DIR / "chinh_sach_nhan_su_va_van_hanh_2025.docx"
        if not sample_path.exists():
            print(f"Sample file not found at {sample_path}, skipping docx test.")
            return

        # 2. Extract and check chunks
        pages = self.engine.loader.load_document(sample_path)
        self.assertTrue(len(pages) > 0)
        doc_id = pages[0].doc_id
        chunks = self.engine.chunker.chunk_documents(pages)
        self.assertTrue(len(chunks) > 0)
        total_chunks = len(chunks)
        print(f"Total chunks for '{sample_path.name}': {total_chunks}")

        # Ensure clean state for test doc
        self.engine.vector_store.delete_document(doc_id)
        existing = self.engine.vector_store.get_existing_chunk_ids(doc_id)
        self.assertEqual(len(existing), 0)

        # 3. Simulate partial indexing: index only the first 2 chunks
        partial_chunks = chunks[:2]
        partial_texts = [c.text for c in partial_chunks]
        partial_embeds = self.engine.embedding.embed_batch(partial_texts)
        self.engine.vector_store.add_chunks(partial_chunks, embeddings=partial_embeds)

        existing_after_partial = self.engine.vector_store.get_existing_chunk_ids(doc_id)
        self.assertEqual(len(existing_after_partial), 2)
        print(f"Partial indexing verified: {len(existing_after_partial)}/2 chunks stored.")

        # 4. Now call index_document without force_reindex
        # It should detect existing 2 chunks, resume and index ONLY the remaining chunks!
        callback_history = []
        def progress_cb(current, total, msg):
            callback_history.append((current, total, msg))

        res = self.engine.index_document(
            sample_path,
            force_reindex=False,
            progress_callback=progress_cb,
            batch_size=5
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["chunk_count"], total_chunks)
        self.assertEqual(res["newly_added"], total_chunks - 2)
        print(f"Resumed indexing succeeded: newly added = {res['newly_added']}, total = {res['chunk_count']}")
        self.assertTrue(len(callback_history) > 0)
        print(f"Progress callback fired {len(callback_history)} times.")

        # 5. Call index_document again: Should immediately return 'already_indexed'
        res_already = self.engine.index_document(sample_path, force_reindex=False)
        self.assertEqual(res_already["status"], "already_indexed")
        print("Already indexed check verified: status = 'already_indexed'")


if __name__ == "__main__":
    unittest.main()
