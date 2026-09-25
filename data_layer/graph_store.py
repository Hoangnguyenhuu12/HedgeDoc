"""
Legal Lineage & Knowledge Graph Store (Principle 9: Tiered Relation Extraction & Legal Validity).
Stores document metadata, regulatory relations (REPLACES, AMENDS, ABROGATES, BASES_ON),
and provides deterministic legal status warnings to prevent citing obsolete documents.
Backed by lightweight, embedded SQLite (WAL Mode, zero extra RAM overhead).
"""

import sqlite3
from contextlib import contextmanager
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Regex for official document numbers (e.g. 15/2021/NĐ-CP, 45/QĐ-UBND, 02/2024/TT-BXD, QCP-HR-2024)
DOC_NUMBER_PATTERN = re.compile(
    r'(?i)(?:Số|Số hiệu|Quyết định số|Thông tư số|Nghị định số|Quy chế số)?\s*[:.]?\s*([0-9]{1,4}/[0-9]{4}/[a-zA-Z0-9đĐ\-_/]+|[0-9]{1,4}/[a-zA-Z0-9đĐ\-_/]+|[a-zA-Z0-9đĐ]{2,4}-[a-zA-Z0-9đĐ\-_/]+)',
    re.UNICODE
)

# Relational patterns (Tier 1: Deterministic Pattern Matching)
RELATION_PATTERNS = [
    (
        "REPLACES",
        re.compile(
            r'(?i)(?:thay thế|thay the)\s+(?:hoàn toàn\s+)?(?:cho\s+)?(?:Quyết định|Thông tư|Nghị định|Văn bản|Quy chế|Chính sách)?\s*(?:số)?\s*[:.]?\s*([0-9]{1,4}/[0-9]{4}/[a-zA-Z0-9đĐ\-_/]+|[0-9]{1,4}/[a-zA-Z0-9đĐ\-_/]+|[a-zA-Z0-9đĐ]{2,4}-[a-zA-Z0-9đĐ\-_/]+)',
            re.UNICODE
        )
    ),
    (
        "ABROGATES",
        re.compile(
            r'(?i)(?:bãi bỏ|hủy bỏ|bai bo|huy bo)\s+(?:toàn bộ\s+)?(?:Quyết định|Thông tư|Nghị định|Văn bản|Quy chế|Chính sách)?\s*(?:số)?\s*[:.]?\s*([0-9]{1,4}/[0-9]{4}/[a-zA-Z0-9đĐ\-_/]+|[0-9]{1,4}/[a-zA-Z0-9đĐ\-_/]+|[a-zA-Z0-9đĐ]{2,4}-[a-zA-Z0-9đĐ\-_/]+)',
            re.UNICODE
        )
    ),
    (
        "AMENDS",
        re.compile(
            r'(?i)(?:sửa đổi|bổ sung|sua doi|bo sung)\s+(?:một số điều của\s+)?(?:Quyết định|Thông tư|Nghị định|Văn bản|Quy chế|Chính sách)?\s*(?:số)?\s*[:.]?\s*([0-9]{1,4}/[0-9]{4}/[a-zA-Z0-9đĐ\-_/]+|[0-9]{1,4}/[a-zA-Z0-9đĐ\-_/]+|[a-zA-Z0-9đĐ]{2,4}-[a-zA-Z0-9đĐ\-_/]+)',
            re.UNICODE
        )
    ),
    (
        "BASES_ON",
        re.compile(
            r'(?i)(?:căn cứ|can cu)\s+(?:vào\s+)?(?:Luật|Quyết định|Thông tư|Nghị định|Nghị quyết)?\s*(?:số)?\s*[:.]?\s*([0-9]{1,4}/[0-9]{4}/[a-zA-Z0-9đĐ\-_/]+|[0-9]{1,4}/[a-zA-Z0-9đĐ\-_/]+|[a-zA-Z0-9đĐ]{2,4}-[a-zA-Z0-9đĐ\-_/]+)',
            re.UNICODE
        )
    )
]


class LegalLineageStore:
    """
    Manages legal relationships between documents:
    - Lineage graph tracking (Who replaces/amends whom).
    - Status verification (Active, Superseded, Amended).
    - Executive Alert Generation (Warning if user asks about invalidated provisions).
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            from config import config
            db_path = config.VECTOR_STORE_DIR / "legal_lineage.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables for documents and relational lineage edges."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    doc_number TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lineage_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_doc_id TEXT NOT NULL,
                    source_file_name TEXT NOT NULL,
                    target_reference TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    evidence_text TEXT,
                    confidence TEXT DEFAULT 'deterministic',
                    status TEXT DEFAULT 'confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON lineage_edges(target_reference);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON lineage_edges(source_doc_id);")

    def register_document(
        self,
        doc_id: str,
        file_name: str,
        doc_number: Optional[str] = None,
        status: str = "active"
    ) -> None:
        """Register or update document in the master lineage catalog."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO documents (doc_id, file_name, doc_number, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    file_name = excluded.file_name,
                    doc_number = COALESCE(excluded.doc_number, documents.doc_number),
                    status = excluded.status;
            """, (doc_id, file_name, doc_number, status))

    def add_edge(
        self,
        source_doc_id: str,
        source_file_name: str,
        target_reference: str,
        relation_type: str,
        evidence_text: str = "",
        confidence: str = "deterministic"
    ) -> None:
        """Add a legal relationship edge (e.g. source REPLACES target)."""
        clean_target = target_reference.strip().upper()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO lineage_edges (
                    source_doc_id, source_file_name, target_reference,
                    relation_type, evidence_text, confidence
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (source_doc_id, source_file_name, clean_target, relation_type, evidence_text, confidence))

    def extract_and_index_relations(
        self,
        doc_id: str,
        file_name: str,
        full_text: str
    ) -> List[Dict[str, Any]]:
        """
        Scan document text to detect its own document number and any outgoing
        legal relations (REPLACES, AMENDS, ABROGATES, BASES_ON).
        """
        # 1. Identify own document number from first 1000 characters
        header_sample = full_text[:1200]
        doc_number = None
        match_doc_num = DOC_NUMBER_PATTERN.search(header_sample)
        if match_doc_num:
            doc_number = match_doc_num.group(1).strip().upper()

        self.register_document(doc_id, file_name, doc_number)

        # Remove previous edges for this document before re-indexing
        with self._get_connection() as conn:
            conn.execute("DELETE FROM lineage_edges WHERE source_doc_id = ?;", (doc_id,))

        extracted_edges: List[Dict[str, Any]] = []

        # 2. Scan lines/sentences for relational statements (Tier 1)
        sentences = re.split(r'[\n;.]+', full_text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue

            for rel_type, pattern in RELATION_PATTERNS:
                for match in pattern.finditer(s_clean):
                    target_ref = match.group(1).strip().upper()
                    # Skip self-reference
                    if doc_number and target_ref == doc_number:
                        continue

                    self.add_edge(
                        source_doc_id=doc_id,
                        source_file_name=file_name,
                        target_reference=target_ref,
                        relation_type=rel_type,
                        evidence_text=s_clean[:180]
                    )
                    extracted_edges.append({
                        "source": file_name,
                        "relation": rel_type,
                        "target": target_ref,
                        "evidence": s_clean[:180]
                    })

        logger.info(f"LegalLineageStore: Extracted {len(extracted_edges)} relations from '{file_name}'.")
        return extracted_edges

    def get_superseding_documents(self, file_name_or_ref: str) -> List[Dict[str, Any]]:
        """
        Check if a given file name or document reference has been replaced or amended
        by another document in the knowledge base.
        """
        clean_target = file_name_or_ref.strip().upper()
        stem = Path(file_name_or_ref).stem.upper()

        with self._get_connection() as conn:
            # 1. Resolve registered doc_number for this file if available
            cursor_doc = conn.execute(
                "SELECT doc_number FROM documents WHERE file_name = ? OR doc_id = ?;",
                (file_name_or_ref, file_name_or_ref)
            )
            row = cursor_doc.fetchone()
            doc_number = row["doc_number"].strip().upper() if row and row["doc_number"] else None

            # 2. Query edges where target_reference matches doc_number, file_name, or stem
            cursor = conn.execute("""
                SELECT source_file_name, relation_type, target_reference, evidence_text, confidence
                FROM lineage_edges
                WHERE target_reference = ?
                   OR target_reference = ?
                   OR target_reference LIKE ?
                   OR ? LIKE '%' || target_reference || '%'
            """, (clean_target, doc_number or clean_target, f"%{stem}%", stem))
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "source_file_name": r["source_file_name"],
                "relation_type": r["relation_type"],
                "target_reference": r["target_reference"],
                "evidence_text": r["evidence_text"],
                "confidence": r["confidence"]
            })
        return results

    def check_validity_alert(self, cited_files: List[str]) -> Optional[str]:
        """
        Check cited documents for legal obsolescence or amendments.
        If any cited document has been superseded/amended, builds a high-priority
        executive warning banner according to Principle 9 / [INV-HEDGE-04].
        """
        if not cited_files:
            return None

        warnings = []
        for fname in set(cited_files):
            # Check if this document has been superseded or amended
            incoming_edges = self.get_superseding_documents(fname)
            for edge in incoming_edges:
                rel = edge["relation_type"]
                new_doc = edge["source_file_name"]
                evidence = edge.get("evidence_text", "")

                if rel in ["REPLACES", "ABROGATES"]:
                    warnings.append(
                        f"- ⚠️ **CẢNH BÁO HIỆU LỰC PHÁP LÝ**: Văn bản `{fname}` đã bị **THAY THẾ / BÃI BỎ** bởi `{new_doc}`. "
                        f"Nội dung trích dẫn dưới đây có thể đã **HẾT HIỆU LỰC HIỆN HÀNH**.\n  *(Căn cứ: \"{evidence}\")*"
                    )
                elif rel == "AMENDS":
                    warnings.append(
                        f"- ℹ️ **LƯU Ý HIỆU LỰC**: Văn bản `{fname}` đã được **SỬA ĐỔI / BỔ SUNG** bởi `{new_doc}`. "
                        f"Cần đối chiếu với văn bản mới để xác định quy định hiện hành.\n  *(Căn cứ: \"{evidence}\")*"
                    )

        if warnings:
            return "\n\n".join(warnings)
        return None

    def get_all_edges_summary(self) -> List[Dict[str, Any]]:
        """Return all legal relationship edges for UI or inspection."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT source_file_name, relation_type, target_reference, evidence_text
                FROM lineage_edges
                ORDER BY created_at DESC;
            """)
            return [dict(r) for r in cursor.fetchall()]
