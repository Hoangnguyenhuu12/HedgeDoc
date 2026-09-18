"""
Sentence-Boundary Semantic Chunker.
Splits document pages into cohesive chunks tagged with page numbers and chunk IDs.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from .loader import ExtractedPage


@dataclass
class DocumentChunk:
    """Represents a text segment with full metadata for citations."""
    chunk_id: str
    doc_id: str
    file_name: str
    page_number: int
    text: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentChunker:
    """
    Chunks document text along natural sentence and paragraph boundaries
    while strictly preserving 100% source page metadata.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _find_split_point(self, text: str, target_pos: int) -> int:
        """
        Find the nearest natural split boundary (paragraph break, period, punctuation, space)
        to prevent splitting words or sentences abruptly.
        """
        if target_pos >= len(text):
            return len(text)

        # Prioritize paragraph breaks
        paragraph_break = text.rfind("\n\n", 0, target_pos)
        if paragraph_break > target_pos * 0.7:
            return paragraph_break + 2

        # Look for sentence-ending punctuation (. ? !)
        for punct in [". ", "? ", "! ", ".\n", "?\n", "!\n"]:
            punct_pos = text.rfind(punct, 0, target_pos)
            if punct_pos > target_pos * 0.6:
                return punct_pos + len(punct)

        # Fallback to whitespace to prevent word severance
        space_pos = text.rfind(" ", 0, target_pos)
        if space_pos > target_pos * 0.5:
            return space_pos + 1

        # Worst-case scenario (very long uninterrupted token)
        return target_pos

    def chunk_page(self, page: ExtractedPage) -> List[DocumentChunk]:
        """Split a single page into chunks."""
        text = page.text
        chunks: List[DocumentChunk] = []
        start_idx = 0
        chunk_idx = 0

        while start_idx < len(text):
            target_end = start_idx + self.chunk_size
            split_end = self._find_split_point(text, target_end)

            chunk_text = text[start_idx:split_end].strip()

            if chunk_text:
                chunk_id = f"{page.doc_id}_p{page.page_number}_c{chunk_idx}"
                loc_label = getattr(page, "location_label", None) or f"Trang {page.page_number}"
                metadata = {
                    "doc_id": page.doc_id,
                    "file_name": page.file_name,
                    "page_number": page.page_number,
                    "location_label": loc_label,
                    "total_pages": page.total_pages,
                    "chunk_id": chunk_id,
                    "char_count": len(chunk_text),
                }

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=page.doc_id,
                        file_name=page.file_name,
                        page_number=page.page_number,
                        text=chunk_text,
                        metadata=metadata,
                    )
                )
                chunk_idx += 1

            if split_end >= len(text):
                break

            # Advance sliding pointer with overlap offset
            step = (split_end - start_idx) - self.chunk_overlap
            start_idx += max(1, step)

        return chunks

    def chunk_documents(self, pages: List[ExtractedPage]) -> List[DocumentChunk]:
        """Split a collection of extracted pages into chunks."""
        all_chunks: List[DocumentChunk] = []
        for page in pages:
            page_chunks = self.chunk_page(page)
            all_chunks.extend(page_chunks)
        return all_chunks
