"""
Structure-Aware Parent-Child Semantic Chunker (Principle 8).
Splits document pages into hierarchical Parent-Child blocks:
- Child chunks (~300-400 chars): Precision vector indexing & BM25 keyword matching.
- Parent chunks (~800-1500 chars): Complete semantic context (Articles, Sections, Tables) expanded for LLM generation.
- Preserves structure paths (struct_path) like 'Điều 5 > Khoản 2' and table integrity.
"""

import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from .loader import ExtractedPage

# Patterns for legal articles, sections, and structural headers
ARTICLE_PATTERN = re.compile(
    r'(?m)^(?:\s*)(?:(ĐIỀU|Điều|ARTICLE|Article|KHOẢN|Khoản|MỤC|Mục|CHƯƠNG|Chương|PHẦN|Phần)\s+([0-9IVXLCDM]+[a-z]?)[.:\s\-])',
    re.UNICODE
)

HEADING_PATTERN = re.compile(
    r'(?m)^(?:\s*)(?:#{1,4}\s+|(?:\d+\.)+\d*\s+|[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]{4,}:)',
    re.UNICODE
)


@dataclass
class DocumentChunk:
    """Represents a text segment with full metadata for citations and parent expansion."""
    chunk_id: str
    doc_id: str
    file_name: str
    page_number: int
    text: str
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None
    struct_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentChunker:
    """
    Structure-Aware Parent-Child Semantic Chunker.
    Deconstructs documents along hierarchical boundaries:
    1. Parent Level: Full Articles, Sections, or Tables (~800-1500 chars)
    2. Child Level: Granular search chunks (~300-400 chars, overlap=0)
    """

    def __init__(
        self,
        chunk_size: int = 900,
        chunk_overlap: int = 150,
        child_size: int = 380
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.child_size = child_size

    def _find_split_point(self, text: str, start_pos: int, target_pos: int) -> int:
        """Find the nearest natural split boundary (punctuation, paragraph, space)."""
        if target_pos >= len(text):
            return len(text)

        min_progress = max(start_pos + int(self.child_size * 0.4), start_pos + 1)
        if min_progress >= target_pos:
            return target_pos

        # Paragraph break
        paragraph_break = text.rfind("\n\n", min_progress, target_pos)
        if paragraph_break != -1:
            return paragraph_break + 2

        # Sentence-ending punctuation
        for punct in [". ", "? ", "! ", ".\n", "?\n", "!\n", ";\n"]:
            punct_pos = text.rfind(punct, min_progress, target_pos)
            if punct_pos != -1:
                return punct_pos + len(punct)

        # Whitespace
        space_pos = text.rfind(" ", min_progress, target_pos)
        if space_pos != -1:
            return space_pos + 1

        return target_pos

    def _extract_parent_blocks(self, page: ExtractedPage) -> List[Dict[str, Any]]:
        """
        Segment page text into coherent parent blocks based on structural markers
        (Articles, Headings, Tables, or Paragraph clusters).
        """
        text = page.text.strip()
        if not text:
            return []

        base_loc = getattr(page, "location_label", None) or f"Trang {page.page_number}"

        # 1. Excel spreadsheets or tables are treated as atomic parent blocks
        if page.file_name.lower().endswith((".xlsx", ".xls")) or (text.startswith("|") and "\n|" in text):
            return [{
                "text": text,
                "struct_path": base_loc,
                "location_label": base_loc,
                "is_table": True
            }]

        # 2. Check for structural boundaries (Articles: Điều/Khoản or Headings)
        splits = []
        for match in ARTICLE_PATTERN.finditer(text):
            label = match.group(0).strip(".:- \t\n")
            splits.append((match.start(), label))

        if not splits:
            # Try Markdown or numbered headings
            for match in HEADING_PATTERN.finditer(text):
                label = match.group(0).strip(".:- \t\n#")
                if len(label) < 60:
                    splits.append((match.start(), label))

        # 3. If explicit structures found, partition into parent blocks
        if splits:
            # Sort by start offset
            splits.sort(key=lambda x: x[0])
            parent_blocks = []
            
            # Text before the first heading (if any)
            if splits[0][0] > 60:
                pre_text = text[:splits[0][0]].strip()
                if pre_text:
                    parent_blocks.append({
                        "text": pre_text,
                        "struct_path": base_loc,
                        "location_label": base_loc,
                        "is_table": False
                    })

            for idx, (start, label) in enumerate(splits):
                end = splits[idx + 1][0] if idx + 1 < len(splits) else len(text)
                block_content = text[start:end].strip()
                if block_content:
                    struct_path = f"{base_loc} › {label}" if base_loc != label else label
                    parent_blocks.append({
                        "text": block_content,
                        "struct_path": struct_path,
                        "location_label": struct_path,
                        "is_table": False
                    })
            return parent_blocks

        # 4. Fallback: Group by natural paragraphs (~800-1200 chars)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        parent_blocks = []
        current_group = []
        current_len = 0

        for p in paragraphs:
            if current_len + len(p) > self.chunk_size and current_group:
                full_group_text = "\n\n".join(current_group)
                parent_blocks.append({
                    "text": full_group_text,
                    "struct_path": base_loc,
                    "location_label": base_loc,
                    "is_table": False
                })
                current_group = [p]
                current_len = len(p)
            else:
                current_group.append(p)
                current_len += len(p)

        if current_group:
            full_group_text = "\n\n".join(current_group)
            parent_blocks.append({
                "text": full_group_text,
                "struct_path": base_loc,
                "location_label": base_loc,
                "is_table": False
            })

        return parent_blocks

    def chunk_page(self, page: ExtractedPage) -> List[DocumentChunk]:
        """
        Split a single page into Structure-Aware Parent-Child chunks.
        """
        parent_blocks = self._extract_parent_blocks(page)
        all_chunks: List[DocumentChunk] = []

        for p_idx, p_block in enumerate(parent_blocks):
            p_text = p_block["text"]
            struct_path = p_block["struct_path"]
            loc_label = p_block["location_label"]
            parent_id = f"{page.doc_id}_p{page.page_number}_par{p_idx}"

            # If block is small enough or is an intact table, keep 1:1 parent-child
            if len(p_text) <= self.child_size or p_block.get("is_table"):
                chunk_id = f"{parent_id}_c0"
                metadata = {
                    "doc_id": page.doc_id,
                    "file_name": page.file_name,
                    "page_number": page.page_number,
                    "location_label": loc_label,
                    "struct_path": struct_path,
                    "parent_id": parent_id,
                    "parent_text": p_text,
                    "total_pages": page.total_pages,
                    "chunk_id": chunk_id,
                    "char_count": len(p_text),
                    "is_child": False
                }
                all_chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=page.doc_id,
                        file_name=page.file_name,
                        page_number=page.page_number,
                        text=p_text,
                        metadata=metadata,
                        parent_id=parent_id,
                        struct_path=struct_path
                    )
                )
                continue

            # Otherwise, partition parent into granular child chunks for sharp retrieval
            start_pos = 0
            child_idx = 0
            while start_pos < len(p_text):
                target_end = start_pos + self.child_size
                split_end = self._find_split_point(p_text, start_pos, target_end)
                child_text = p_text[start_pos:split_end].strip()

                if child_text:
                    chunk_id = f"{parent_id}_c{child_idx}"
                    metadata = {
                        "doc_id": page.doc_id,
                        "file_name": page.file_name,
                        "page_number": page.page_number,
                        "location_label": loc_label,
                        "struct_path": struct_path,
                        "parent_id": parent_id,
                        "parent_text": p_text,  # Enables LLM expansion to parent context
                        "total_pages": page.total_pages,
                        "chunk_id": chunk_id,
                        "char_count": len(child_text),
                        "is_child": True
                    }
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=page.doc_id,
                            file_name=page.file_name,
                            page_number=page.page_number,
                            text=child_text,
                            metadata=metadata,
                            parent_id=parent_id,
                            struct_path=struct_path
                        )
                    )
                    child_idx += 1

                if split_end >= len(p_text):
                    break
                # Under Parent-Child architecture, children have overlap=0 to prevent bloated indices
                start_pos = split_end

        return all_chunks

    def chunk_documents(self, pages: List[ExtractedPage]) -> List[DocumentChunk]:
        """Split a collection of extracted pages into Parent-Child chunks."""
        all_chunks: List[DocumentChunk] = []
        for page in pages:
            page_chunks = self.chunk_page(page)
            all_chunks.extend(page_chunks)
        return all_chunks
