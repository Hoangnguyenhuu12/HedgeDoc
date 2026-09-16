"""
Persistent Vector Database Management (ChromaDB Manager).
Stores vector embeddings persistently and performs Cosine similarity search without generating embeddings or parsing PDFs.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from .chunker import DocumentChunk


class VectorStoreManager:
    """
    Manages embedding storage and context retrieval using ChromaDB.
    Supports document-level metadata filtering and multi-file management.
    """

    def __init__(
        self,
        persist_directory: Path,
        collection_name: str = "hedgedoc_knowledge_base"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name

        # Initialize Persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use Cosine distance
        )

    def is_document_indexed(self, doc_id: str) -> bool:
        """Check whether a document with the given doc_id exists in the vector database."""
        existing = self.collection.get(
            where={"doc_id": doc_id},
            limit=1
        )
        return len(existing["ids"]) > 0

    def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: Optional[List[List[float]]] = None
    ) -> int:
        """
        Add DocumentChunk items into the vector store.
        If embeddings are provided, they are stored directly alongside the chunks.
        """
        if not chunks:
            return 0

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # ChromaDB batch size limits: chunk into safe batches
        batch_size = 200
        total_added = 0

        for i in range(0, len(chunks), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_embeds = embeddings[i:i + batch_size] if embeddings else None

            if batch_embeds:
                self.collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas,
                    embeddings=batch_embeds
                )
            else:
                self.collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas
                )
            total_added += len(batch_ids)

        return total_added

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        doc_id_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for the most semantically similar chunks.

        Args:
            query_embedding: Vector embedding of the user query.
            top_k: Number of retrieved results.
            doc_id_filter: Optional document ID to restrict search scope.
        """
        where_clause = {"doc_id": doc_id_filter} if doc_id_filter else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        formatted_results: List[Dict[str, Any]] = []

        if results and results["ids"] and results["ids"][0]:
            num_results = len(results["ids"][0])
            for idx in range(num_results):
                formatted_results.append({
                    "chunk_id": results["ids"][0][idx],
                    "text": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx],
                    "distance": results["distances"][0][idx] if results.get("distances") else None,
                })

        return formatted_results

    def get_indexed_documents_summary(self) -> List[Dict[str, Any]]:
        """Retrieve a summary of all indexed documents in the database."""
        all_data = self.collection.get(include=["metadatas"])
        docs_summary: Dict[str, Dict[str, Any]] = {}

        if all_data and all_data.get("metadatas"):
            for meta in all_data["metadatas"]:
                doc_id = meta.get("doc_id")
                if not doc_id:
                    continue

                if doc_id not in docs_summary:
                    docs_summary[doc_id] = {
                        "doc_id": doc_id,
                        "file_name": meta.get("file_name", "Unknown"),
                        "total_pages": meta.get("total_pages", 0),
                        "chunk_count": 0,
                    }
                docs_summary[doc_id]["chunk_count"] += 1

        return list(docs_summary.values())

    def delete_document(self, doc_id: str) -> None:
        """Delete all chunks associated with a specific document ID."""
        self.collection.delete(where={"doc_id": doc_id})

    def clear_all(self) -> None:
        """Clear all records from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
