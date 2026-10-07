"""
Client adapter for Document RAG Engine.
Supports direct local Python module execution or remote HTTP REST service.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

from HedgeDoc.configs.app_config import config
from HedgeDoc.services.engine_loader import get_rag_pipeline


class RAGClient:
    """
    Client for interacting with Document RAG Engine.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or config.RAG_ENGINE_API_URL
        self._local_pipeline = None

    def _get_local_pipeline(self):
        if self._local_pipeline is None:
            self._local_pipeline = get_rag_pipeline()
        return self._local_pipeline

    def index_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Index a native document directly into RAG vector store.
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        if self.api_url:
            try:
                url = f"{self.api_url.rstrip('/')}/rag/index"
                with open(file_path, "rb") as f:
                    resp = requests.post(url, files={"file": f}, timeout=60)
                resp.raise_for_status()
                return resp.json()
            except Exception:
                pass

        pipeline = self._get_local_pipeline()
        doc = pipeline.loader.load_file(file_path)
        chunk_count = pipeline.index_document(doc)
        return {
            "status": "success",
            "file_name": file_path.name,
            "chunk_count": chunk_count
        }

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents currently persisted in the RAG vector store.
        """
        try:
            pipeline = self._get_local_pipeline()
            dim = pipeline.embedding_provider.dimension
            return pipeline.vector_store.list_indexed_documents(dim)
        except Exception:
            return []

    def delete_document(self, file_name: str) -> bool:
        """
        Delete a document and all its chunks from the RAG vector store.
        """
        try:
            pipeline = self._get_local_pipeline()
            dim = pipeline.embedding_provider.dimension
            return pipeline.vector_store.delete_document(file_name, dim)
        except Exception:
            return False

    def clear_all_documents(self) -> bool:
        """
        Clear all documents from the RAG vector store.
        """
        try:
            pipeline = self._get_local_pipeline()
            dim = pipeline.embedding_provider.dimension
            return pipeline.vector_store.clear_all_documents(dim)
        except Exception:
            return False

    def index_ocr_output(self, ocr_data: Dict[str, Any], source_path: str = "ocr_document") -> Dict[str, Any]:
        """
        Index standardized OCROutput JSON into RAG.
        """
        if self.api_url:
            try:
                url = f"{self.api_url.rstrip('/')}/rag/index-ocr"
                resp = requests.post(
                    url,
                    json={"ocr_data": ocr_data, "source_path": str(source_path)},
                    timeout=60
                )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                pass

        pipeline = self._get_local_pipeline()
        doc = pipeline.loader.load_from_ocr_json(ocr_data, source_path=source_path)
        chunk_count = pipeline.index_document(doc)
        return {
            "status": "success",
            "file_name": str(source_path),
            "chunk_count": chunk_count
        }

    def query(
        self,
        query_text: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG engine with hybrid retrieval and synthesis.
        """
        if self.api_url:
            try:
                url = f"{self.api_url.rstrip('/')}/rag/query"
                resp = requests.post(
                    url,
                    json={"query": query_text, "top_k": top_k, "chat_history": chat_history},
                    timeout=60
                )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                pass

        pipeline = self._get_local_pipeline()
        import doc_rag_pkg.schemas.rag_contracts as rag_contracts
        req = rag_contracts.RAGQueryRequest(query=query_text, top_k=top_k)
        res = pipeline.query(req)

        citations_list = []
        for c in res.citations:
            citations_list.append({
                "source": c.doc_name,
                "page": c.page_number,
                "score": c.score,
                "text": c.text_snippet
            })

        return {
            "answer": res.answer,
            "citations": citations_list,
            "mode": res.mode,
            "model_used": res.model_used,
            "latency_seconds": res.latency_seconds
        }

    def stream_query(
        self,
        query_text: str,
        top_k: int = 4,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[List[Dict[str, Any]], Any]:
        """
        Executes hybrid retrieval and streams response tokens in real-time.
        Returns:
            Tuple of (citations_list, token_generator)
        """
        pipeline = self._get_local_pipeline()
        import doc_rag_pkg.schemas.rag_contracts as rag_contracts

        req = rag_contracts.RAGQueryRequest(
            query=query_text,
            top_k=top_k,
            conversation_history=chat_history
        )

        stream_gen = pipeline.stream_query(req)
        # First yielded element is always List[Citation]
        raw_citations = next(stream_gen)
        citations_list = []
        for c in raw_citations:
            citations_list.append({
                "source": c.doc_name,
                "page": c.page_number,
                "score": c.score,
                "text": c.text_snippet
            })

        return citations_list, stream_gen

