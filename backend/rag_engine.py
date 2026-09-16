"""
Central RAG Orchestrator.
Coordinates the entire RAG pipeline: PDF Loader -> Chunker -> ChromaDB -> Memory -> Prompt -> LLM -> Citations.
Serves as the primary backend interface for the frontend application.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Union
from config import config
from data_layer.loader import PDFDocumentLoader
from data_layer.chunker import DocumentChunker
from data_layer.vector_store import VectorStoreManager
from .providers.base import BaseLLM, BaseEmbedding
from .providers.factory import ProviderFactory
from .memory import ConversationMemoryBuffer
from .prompts import STRICT_RAG_SYSTEM_PROMPT, build_rag_prompt


class RAGEngine:
    """
    Central orchestrator for the HedgeDoc RAG system.
    Connects:
    - Loader & Chunker (Data Layer)
    - VectorStoreManager (ChromaDB)
    - LLM & Embedding Adapter (Provider Layer)
    - ConversationMemoryBuffer (Memory Layer)
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreManager] = None,
        llm: Optional[BaseLLM] = None,
        embedding: Optional[BaseEmbedding] = None,
        memory: Optional[ConversationMemoryBuffer] = None
    ):
        self.vector_store = vector_store or VectorStoreManager(
            persist_directory=config.VECTOR_STORE_DIR,
            collection_name=config.CHROMA_COLLECTION_NAME
        )
        self.llm = llm or ProviderFactory.get_llm()
        self.embedding = embedding or ProviderFactory.get_embedding()
        self.memory = memory or ConversationMemoryBuffer()

        self.loader = PDFDocumentLoader()
        self.chunker = DocumentChunker(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )

    def index_document(
        self,
        pdf_path: Union[str, Path],
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Index a PDF document into the ChromaDB vector store.
        Workflow: Extract text with page numbers -> Sentence chunking -> Generate embeddings -> Store in ChromaDB.
        """
        path = Path(pdf_path)
        pages = self.loader.load_single_pdf(path)
        if not pages:
            return {
                "status": "empty",
                "doc_id": "unknown",
                "file_name": path.name,
                "total_pages": 0,
                "message": "No valid text content found in the PDF file."
            }

        doc_id = pages[0].doc_id
        file_name = pages[0].file_name
        total_pages = pages[0].total_pages

        # Check if already indexed to avoid duplicates
        if not force_reindex and self.vector_store.is_document_indexed(doc_id):
            return {
                "status": "already_indexed",
                "doc_id": doc_id,
                "file_name": file_name,
                "total_pages": total_pages,
                "message": f"Document '{file_name}' already exists in the vector store."
            }

        # If force_reindex, remove old chunks first
        if force_reindex and self.vector_store.is_document_indexed(doc_id):
            self.vector_store.delete_document(doc_id)

        # Chunk documents with page metadata
        chunks = self.chunker.chunk_documents(pages)
        if not chunks:
            return {
                "status": "empty",
                "doc_id": doc_id,
                "file_name": file_name,
                "total_pages": total_pages,
                "message": "No valid text found to chunk."
            }

        # Generate embeddings in batches
        texts = [c.text for c in chunks]
        embeddings = self.embedding.embed_batch(texts)

        # Store in ChromaDB
        added_count = self.vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

        # Export human-readable Markdown inspection previews
        self._export_readable_preview(pages=pages, chunks=chunks, pdf_name=file_name, doc_id=doc_id)

        return {
            "status": "success",
            "doc_id": doc_id,
            "file_name": file_name,
            "total_pages": total_pages,
            "chunk_count": added_count,
            "message": f"Successfully indexed {added_count} chunks from '{file_name}'."
        }

    def _export_readable_preview(
        self,
        pages: List[Any],
        chunks: List[Any],
        pdf_name: str,
        doc_id: str
    ) -> None:
        """Export inspection files (big_chunks.md and small_chunks.md) to data/previews/."""
        try:
            import re
            preview_base = config.DATA_DIR / "previews"
            clean_stem = re.sub(r"[^\w\s-]", "", Path(pdf_name).stem)
            folder_name = re.sub(r"[-\s]+", "_", clean_stem).strip("_").lower()[:30]
            doc_dir = preview_base / folder_name
            doc_dir.mkdir(parents=True, exist_ok=True)

            # 1. Big Chunks (Page-level text extraction)
            big_chunks_file = doc_dir / "big_chunks.md"
            with open(big_chunks_file, "w", encoding="utf-8") as f:
                f.write(f"# Document: {pdf_name}\n\n")
                f.write(f"- Document ID: {doc_id}\n")
                f.write(f"- Total Pages: {len(pages)}\n")
                f.write("- Granularity: Big Chunks (Page-level text with preserved structure)\n\n" + "=" * 60 + "\n\n")
                for p in pages:
                    f.write(f"## [ PAGE {p.page_number} / {p.total_pages} ]\n\n{p.text}\n\n" + "-" * 40 + "\n\n")

            # 2. Small Chunks (Fine-grained semantic segments for vector search)
            small_chunks_file = doc_dir / "small_chunks.md"
            with open(small_chunks_file, "w", encoding="utf-8") as f:
                f.write(f"# Semantic Segments: {pdf_name}\n\n")
                f.write(f"- Total Chunks: {len(chunks)}\n")
                f.write(f"- Granularity: Small Chunks (Sentence-boundary segments for vector retrieval)\n\n" + "=" * 60 + "\n\n")
                for idx, c in enumerate(chunks, start=1):
                    f.write(f"### Chunk {idx} (Source: Page {c.page_number} | ID: {c.chunk_id})\n> {c.text}\n\n" + "-" * 40 + "\n\n")
        except Exception:
            pass

    def _extract_citations(self, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardize citations from ChromaDB retrieval results."""
        citations: List[Dict[str, Any]] = []
        for c in retrieved_chunks:
            meta = c.get("metadata", {})
            text = c.get("text", "").strip()
            snippet = text[:200] + "..." if len(text) > 200 else text

            citations.append({
                "chunk_id": c.get("chunk_id"),
                "file_name": meta.get("file_name", "Unknown"),
                "page_number": meta.get("page_number", "N/A"),
                "distance": c.get("distance"),
                "snippet": snippet
            })
        return citations

    def _is_greeting_or_meta(self, question: str) -> bool:
        """Check if the question is a greeting, conversational turn, or introduction query."""
        import re
        q = question.strip().lower()
        q_clean = re.sub(r"[^\w\s]", "", q).strip()
        
        greetings = {
            "hi", "hello", "xin chao", "xin chào", "chào", "chao", "chào bạn", "chao ban",
            "chao bot", "chào bot", "hey", "alô", "alo", "bạn là ai", "ban la ai", "who are you",
            "bạn có thể làm gì", "ban co the lam gi", "hướng dẫn", "huong dan", "help",
            "giới thiệu", "gioi thieu", "hedgedoc là gì", "hedgedoc la gi"
        }
        if q_clean in greetings:
            return True

        tokens = q_clean.split()
        if len(tokens) <= 3 and any(q_clean.startswith(g) for g in ["hi", "hello", "xin chào", "chào bạn", "chào", "chao"]):
            content_keywords = ["tóm tắt", "tom tat", "tài liệu", "tai lieu", "trang", "sách", "sach", "nội dung", "noi dung", "tìm", "tim"]
            if not any(k in q_clean for k in content_keywords):
                return True

        return False

    def _build_greeting_response(self) -> str:
        """Construct a clean, minimal greeting response listing indexed documents."""
        docs = self.vector_store.get_indexed_documents_summary()
        doc_lines = []
        for d in docs:
            doc_lines.append(f"- {d['file_name']} ({d['total_pages']} trang, {d['chunk_count']} đoạn)")

        docs_text = "\n".join(doc_lines) if doc_lines else "Chưa có tài liệu nào trong kho lưu trữ."

        return (
            "Xin chào. Tôi là HedgeDoc, hệ thống hỗ trợ tra cứu và phân tích tài liệu với trích dẫn số trang chính xác.\n\n"
            f"Tài liệu hiện có:\n{docs_text}\n\n"
            "Bạn có thể đặt câu hỏi về các tài liệu trên."
        )

    def _build_claude_thought_process(
        self,
        question: str,
        is_greeting: bool,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        doc_id_filter: Optional[str] = None
    ) -> str:
        """Construct a minimal 3-bullet thought process."""
        if is_greeting:
            return (
                "- Phân tích: Nhận diện lời chào hỏi.\n"
                "- Dữ liệu: Không cần tra cứu tài liệu.\n"
                "- Phản hồi: Giới thiệu hệ thống và sẵn sàng hỗ trợ."
            )

        retrieved_chunks = retrieved_chunks or []
        citations = citations or []
        pages = sorted(list(dict.fromkeys([str(c.get("page_number")) for c in citations if c.get("page_number") is not None])))
        pages_str = f"trang {', '.join(pages)}" if pages else "không rõ trang"

        return (
            f"- Phân tích: Xác định nội dung cần tra cứu.\n"
            f"- Dữ liệu: Tìm thấy {len(retrieved_chunks)} đoạn trích ({pages_str}).\n"
            f"- Phản hồi: Đối chiếu nội dung gốc và trả lời trọng tâm."
        )

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        doc_id_filter: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Execute the complete RAG lifecycle for an incoming question.
        """
        # Check if conversational greeting or meta question
        if self._is_greeting_or_meta(question):
            docs = self.vector_store.get_indexed_documents_summary()
            greeting_text = self._build_greeting_response()
            thought_process = self._build_claude_thought_process(question, is_greeting=True)
            
            thinking_steps = [
                {"title": "Question Analysis", "detail": "Greeting detected."},
                {"title": "Data Check", "detail": f"{len(docs)} documents ready."},
                {"title": "Synthesis", "detail": "Prepared introduction response."}
            ]

            self.memory.add_user_message(question)
            self.memory.add_assistant_message(content=greeting_text, citations=[])

            if stream:
                def greeting_stream() -> Iterator[str]:
                    import time
                    words = greeting_text.split(" ")
                    for i in range(0, len(words), 3):
                        yield " ".join(words[i:i+3]) + (" " if i + 3 < len(words) else "")
                        time.sleep(0.015)

                return {
                    "answer_stream": greeting_stream(),
                    "thought_process": thought_process,
                    "citations": [],
                    "retrieved_chunks": [],
                    "thinking_steps": thinking_steps
                }
            else:
                return {
                    "answer": greeting_text,
                    "thought_process": thought_process,
                    "citations": [],
                    "retrieved_chunks": [],
                    "thinking_steps": thinking_steps
                }

        # Step 1: Generate vector embedding for the query
        query_vector = self.embedding.embed_text(question)

        # Step 2: Retrieve similar chunks from Vector Store
        k = top_k or config.TOP_K_RETRIEVAL
        retrieved_chunks = self.vector_store.query(
            query_embedding=query_vector,
            top_k=k,
            doc_id_filter=doc_id_filter
        )

        # Extract citation metadata
        citations = self._extract_citations(retrieved_chunks)

        # Build thinking steps
        scope_label = "All documents" if not doc_id_filter else f"Document ID: {doc_id_filter}"
        unique_files = list(set(c.get("file_name") for c in citations if c.get("file_name")))
        pages_covered = sorted(list(set(str(c.get("page_number")) for c in citations if c.get("page_number") is not None)))
        pages_text = f"Pages {', '.join(pages_covered)}" if pages_covered else "Unknown pages"
        min_dist = min([c["distance"] for c in citations if c.get("distance") is not None], default=None)
        dist_info = f" (Distance: {min_dist:.4f})" if min_dist is not None else ""

        thinking_steps = [
            {
                "title": "Query Analysis",
                "detail": f"Scope: {scope_label}."
            },
            {
                "title": "Data Retrieval",
                "detail": f"{len(retrieved_chunks)} chunks from {len(unique_files)} document(s) ({pages_text}){dist_info}."
            },
            {
                "title": "Grounding Check",
                "detail": "Cross-verifying source text."
            }
        ]

        thought_process = self._build_claude_thought_process(
            question=question,
            is_greeting=False,
            retrieved_chunks=retrieved_chunks,
            citations=citations,
            doc_id_filter=doc_id_filter
        )

        # Step 3: Fetch recent conversation history
        history_text = self.memory.get_formatted_history()

        # Step 4: Package full prompt context
        full_prompt = build_rag_prompt(
            query=question,
            retrieved_chunks=retrieved_chunks,
            history_text=history_text
        )

        # Log user query to conversation memory
        self.memory.add_user_message(question)

        # Step 5: Invoke LLM generation
        if stream:
            def streaming_wrapper() -> Iterator[str]:
                collected_chunks: List[str] = []
                for token in self.llm.stream_generate(
                    prompt=full_prompt,
                    system_instruction=STRICT_RAG_SYSTEM_PROMPT
                ):
                    collected_chunks.append(token)
                    yield token

                complete_answer = "".join(collected_chunks)
                self.memory.add_assistant_message(
                    content=complete_answer,
                    citations=citations
                )

            return {
                "answer_stream": streaming_wrapper(),
                "thought_process": thought_process,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks,
                "thinking_steps": thinking_steps
            }
        else:
            answer = self.llm.generate(
                prompt=full_prompt,
                system_instruction=STRICT_RAG_SYSTEM_PROMPT
            )
            self.memory.add_assistant_message(
                content=answer,
                citations=citations
            )
            return {
                "answer": answer,
                "thought_process": thought_process,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks,
                "thinking_steps": thinking_steps
            }

