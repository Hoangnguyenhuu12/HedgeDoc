"""
HedgeDoc workflows package.
Contains pipeline orchestrators combining Quality Gate, OCR, and RAG.
"""

from .document_pipeline import DocumentPipelineOrchestrator

__all__ = ["DocumentPipelineOrchestrator"]
