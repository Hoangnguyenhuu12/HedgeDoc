"""
Central RAG Orchestrator.
Coordinates the entire RAG pipeline: PDF Loader -> Chunker -> ChromaDB -> Memory -> Prompt -> LLM -> Citations.
Serves as the primary backend interface for the frontend application.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Union
from config import config
from data_layer.loader import MultiFormatDocumentLoader, PDFDocumentLoader
from data_layer.chunker import DocumentChunker
from data_layer.vector_store import VectorStoreManager
from .providers.base import BaseLLM, BaseEmbedding
from .providers.factory import ProviderFactory
from .memory import ConversationMemoryBuffer
from .prompts import STRICT_RAG_SYSTEM_PROMPT, build_rag_prompt

logger = logging.getLogger(__name__)


def strip_inline_citations(text: str) -> str:
    """
    Remove inline citation brackets like [Source: ...], [Nguồn: ...], [Trang ...]
    from generated text, as citations are displayed separately in the UI.
    """
    import re
    cleaned = re.sub(r"\s*\[(?:Source|Nguồn|Trang|Page|Segment)[^\]]*\]", "", text, flags=re.IGNORECASE)
    return cleaned.strip()


def clean_citation_stream(token_stream: Iterator[str]) -> Iterator[str]:
    """
    Real-time token stream filter that suppresses bracketed citations like
    [Source: ...] or [Nguồn: ...] while streaming tokens to the frontend.
    """
    buffer = ""
    inside_bracket = False
    last_yielded_ends_with_space = False

    for token in token_stream:
        buffer += token
        while True:
            if not inside_bracket:
                if "[" in buffer:
                    prefix, rest = buffer.split("[", 1)
                    if prefix:
                        if last_yielded_ends_with_space and prefix.startswith(" "):
                            prefix = prefix.lstrip(" ")
                        if prefix:
                            yield prefix
                            last_yielded_ends_with_space = prefix.endswith(" ")
                    buffer = "[" + rest
                    inside_bracket = True
                else:
                    if buffer:
                        chunk = buffer
                        if last_yielded_ends_with_space and chunk.startswith(" "):
                            chunk = chunk.lstrip(" ")
                        if chunk:
                            yield chunk
                            last_yielded_ends_with_space = chunk.endswith(" ")
                        buffer = ""
                    break
            else:
                if "]" in buffer:
                    bracket_content, remaining = buffer.split("]", 1)
                    full_tag = bracket_content + "]"
                    lower_tag = full_tag.lower()
                    if any(k in lower_tag for k in ["source", "nguồn", "trang", "page", "segment"]):
                        # Suppress citation tag
                        pass
                    else:
                        yield full_tag
                        last_yielded_ends_with_space = full_tag.endswith(" ")
                    buffer = remaining
                    inside_bracket = False
                else:
                    if len(buffer) > 120:
                        yield buffer
                        last_yielded_ends_with_space = buffer.endswith(" ")
                        buffer = ""
                        inside_bracket = False
                    break

    if buffer:
        lower_tag = buffer.lower()
        if not (inside_bracket and any(k in lower_tag for k in ["source", "nguồn", "trang", "page", "segment"])):
            if last_yielded_ends_with_space and buffer.startswith(" "):
                buffer = buffer.lstrip(" ")
            if buffer:
                yield buffer


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
        self._llm_cache: Dict[str, BaseLLM] = {}
        self.llm = llm or ProviderFactory.get_llm()
        if llm:
            self._llm_cache[f"{config.LLM_PROVIDER}:{llm.model_name}"] = llm
        else:
            self._llm_cache[f"{config.LLM_PROVIDER}:{self.llm.model_name}"] = self.llm
        self.embedding = embedding or ProviderFactory.get_embedding()
        self.memory = memory or ConversationMemoryBuffer()

        self.loader = MultiFormatDocumentLoader()
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
        try:
            pages = self.loader.load_single_pdf(path)
            if not pages:
                return {
                    "status": "empty",
                    "doc_id": "unknown",
                    "file_name": path.name,
                    "total_pages": 0,
                    "message": f"Không tìm thấy nội dung văn bản hợp lệ trong file '{path.name}'."
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
                    "message": f"Tài liệu '{file_name}' đã tồn tại trong kho lưu trữ."
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
                    "message": f"Không thể trích xuất đoạn văn bản từ '{file_name}'."
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
                "message": f"Đã nạp thành công '{file_name}' ({total_pages} trang, {added_count} đoạn dữ liệu)."
            }
        except Exception as e:
            logger.error(f"Error indexing document {path.name}: {e}")
            return {
                "status": "error",
                "doc_id": "error",
                "file_name": path.name,
                "total_pages": 0,
                "message": f"Lỗi nạp file '{path.name}': {str(e)}"
            }

    def delete_document(self, doc_id: str, file_name: Optional[str] = None) -> bool:
        """
        Delete all chunks associated with a document ID from ChromaDB and clean up preview files.
        """
        try:
            self.vector_store.delete_document(doc_id)
            if file_name:
                import re
                import shutil
                preview_base = config.DATA_DIR / "previews"
                clean_stem = re.sub(r"[^\w\s-]", "", Path(file_name).stem)
                folder_name = re.sub(r"[-\s]+", "_", clean_stem).strip("_").lower()[:30]
                doc_dir = preview_base / folder_name
                if doc_dir.exists() and doc_dir.is_dir():
                    shutil.rmtree(doc_dir, ignore_errors=True)
            logger.info(f"Document {doc_id} ('{file_name}') successfully deleted.")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    def clear_all_documents(self) -> bool:
        """Clear all indexed documents from ChromaDB and preview directory."""
        try:
            self.vector_store.clear_all()
            preview_base = config.DATA_DIR / "previews"
            if preview_base.exists():
                import shutil
                for item in preview_base.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
            logger.info("All documents cleared from vector store and previews.")
            return True
        except Exception as e:
            logger.error(f"Error clearing documents: {e}")
            return False

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

            loc_label = meta.get("location_label") or f"Trang {meta.get('page_number', 'N/A')}"
            citations.append({
                "chunk_id": c.get("chunk_id"),
                "file_name": meta.get("file_name", "Unknown"),
                "page_number": meta.get("page_number", "N/A"),
                "location_label": loc_label,
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

    def _detect_doc_filter(self, question: str) -> Optional[str]:
        """Detect if the query explicitly targets a specific indexed document."""
        import re
        import unicodedata

        def remove_accents(input_str: str) -> str:
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

        q_clean = re.sub(r"[^\w\s]", " ", remove_accents(question.lower())).strip()
        docs = self.vector_store.get_indexed_documents_summary()

        for d in docs:
            fname = remove_accents(d["file_name"].lower())
            stem = Path(fname).stem
            clean_stem = re.sub(r"[_\-]", " ", stem).strip()

            if fname in q_clean or clean_stem in q_clean:
                return d["doc_id"]

            stem_words = [w for w in clean_stem.split() if len(w) > 2 and not w.isdigit()]
            if len(stem_words) >= 2:
                matched_count = sum(1 for w in stem_words if w in q_clean)
                if matched_count >= 2 and ("file" in q_clean or "tai lieu" in q_clean or matched_count == len(stem_words)):
                    return d["doc_id"]

        return None

    def _is_cross_document_query(self, question: str) -> bool:
        """
        Detect if the user inquiry requires broad multi-document synthesis or comparison across all indexed documents.
        """
        import unicodedata
        import re

        def remove_accents(input_str: str) -> str:
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

        q = re.sub(r"[^\w\s]", " ", remove_accents(question.lower())).strip()

        cross_patterns = [
            "so sanh", "khac biet", "cac tai lieu", "tat ca tai lieu", "tat ca cac",
            "toan bo tai lieu", "toan bo cac", "kho tai lieu", "tong quan cac", "diem giong",
            "diem khac", "nhung tai lieu", "moi tai lieu", "cac file", "giua cac",
            "co nhung tai lieu nao", "danh sach tai lieu", "tong hop cac", "chu de cot loi",
            "all documents", "compare documents", "across documents", "every document", "each document"
        ]

        return any(p in q for p in cross_patterns)

    def get_llm(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> BaseLLM:
        """
        Retrieve cached LLM adapter or instantiate a new one via ProviderFactory.
        """
        p = (provider or config.LLM_PROVIDER).lower()
        m = model_name or config.LLM_MODEL
        cache_key = f"{p}:{m}"
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = ProviderFactory.get_llm(provider=p, model_name=m)
        return self._llm_cache[cache_key]

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        doc_id_filter: Optional[str] = None,
        stream: bool = False,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete RAG lifecycle for an incoming question.
        Supports dynamic provider and model selection.
        """
        active_llm = self.get_llm(provider=llm_provider, model_name=llm_model)

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

        # Step 2: Retrieve similar chunks from Vector Store (with auto doc detection & cross-doc diversity)
        all_indexed_docs = self.vector_store.get_indexed_documents_summary()
        effective_filter = doc_id_filter or self._detect_doc_filter(question)
        k = top_k or config.TOP_K_RETRIEVAL
        is_cross_doc = not effective_filter and self._is_cross_document_query(question)

        if is_cross_doc and len(all_indexed_docs) > 1:
            retrieved_chunks = []
            per_doc_k = max(2, (k + len(all_indexed_docs) - 1) // len(all_indexed_docs))
            for d in all_indexed_docs:
                doc_chunks = self.vector_store.query(
                    query_embedding=query_vector,
                    top_k=per_doc_k,
                    doc_id_filter=d["doc_id"]
                )
                retrieved_chunks.extend(doc_chunks)
        else:
            retrieved_chunks = self.vector_store.query(
                query_embedding=query_vector,
                top_k=k,
                doc_id_filter=effective_filter
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
        all_doc_names = [d["file_name"] for d in all_indexed_docs] if is_cross_doc else None
        full_prompt = build_rag_prompt(
            query=question,
            retrieved_chunks=retrieved_chunks,
            history_text=history_text,
            all_doc_names=all_doc_names
        )

        # Log user query to conversation memory
        self.memory.add_user_message(question)

        # Step 5: Invoke LLM generation with chosen model
        if stream:
            def streaming_wrapper() -> Iterator[str]:
                collected_chunks: List[str] = []
                raw_stream = active_llm.stream_generate(
                    prompt=full_prompt,
                    system_instruction=STRICT_RAG_SYSTEM_PROMPT
                )
                for token in clean_citation_stream(raw_stream):
                    collected_chunks.append(token)
                    yield token

                complete_answer = "".join(collected_chunks).strip()
                self.memory.add_assistant_message(
                    content=complete_answer,
                    citations=citations
                )

            return {
                "answer_stream": streaming_wrapper(),
                "thought_process": thought_process,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks,
                "thinking_steps": thinking_steps,
                "model_name": active_llm.model_name,
                "provider": llm_provider or config.LLM_PROVIDER
            }
        else:
            raw_answer = active_llm.generate(
                prompt=full_prompt,
                system_instruction=STRICT_RAG_SYSTEM_PROMPT
            )
            answer = strip_inline_citations(raw_answer)
            self.memory.add_assistant_message(
                content=answer,
                citations=citations
            )
            return {
                "answer": answer,
                "thought_process": thought_process,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks,
                "thinking_steps": thinking_steps,
                "model_name": active_llm.model_name,
                "provider": llm_provider or config.LLM_PROVIDER
            }

