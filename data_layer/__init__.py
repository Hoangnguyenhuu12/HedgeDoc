"""
Data Layer package for HedgeDoc.
Handles multi-file PDF extraction, page-level text parsing,
semantic chunking, and ChromaDB vector persistence with metadata traceability.
"""

from .loader import MultiFormatDocumentLoader, PDFDocumentLoader, ExtractedPage
from .chunker import DocumentChunker, DocumentChunk
from .vector_store import VectorStoreManager

__all__ = [
    "MultiFormatDocumentLoader",
    "PDFDocumentLoader",
    "ExtractedPage",
    "DocumentChunker",
    "DocumentChunk",
    "VectorStoreManager",
]
