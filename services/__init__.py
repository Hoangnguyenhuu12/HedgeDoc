"""
Service client adapters for HedgeDoc to connect with core Document AI engines:
- Document Quality Gate
- Document OCR Engine
- Document RAG Engine
"""

from .quality_gate_client import QualityGateClient
from .ocr_client import OCRClient
from .rag_client import RAGClient

__all__ = ["QualityGateClient", "OCRClient", "RAGClient"]
