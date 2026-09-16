# HedgeDoc

HedgeDoc is a standalone, NotebookLM-style Retrieval-Augmented Generation (RAG) system engineered for high factual precision and source traceability. The system enforces strict grounding, accurate page-level citations, and multi-turn conversational context.

## Key Features

- PDF Document Extraction: Preserves original page numbers and layout integrity.
- Sentence-Boundary Chunking: Splits documents along natural linguistic boundaries to preserve context.
- Persistent Vector Storage: Efficient embedding indexing and similarity search powered by ChromaDB.
- Strict Grounding (Zero Hallucination): Answers questions solely based on provided context; transparently declines when information is unavailable.
- Citation Traceability: Every claim links directly to its source document and page number with original snippets.
- Minimalist Interface: Built with Streamlit, supporting low-latency token streaming and a collapsible reasoning drawer.

## System Architecture

```text
HedgeDoc/
├── backend/
│   ├── providers/          # LLM & Embedding provider adapters (Gemini, Factory Pattern)
│   ├── memory.py           # Multi-turn conversation history buffer
│   ├── prompts.py          # Grounded system prompts and citation formatting rules
│   └── rag_engine.py       # Core RAG orchestration pipeline
├── data_layer/
│   ├── loader.py           # Multi-page PDF text extraction
│   ├── chunker.py          # Semantic boundary chunking
│   └── vector_store.py     # ChromaDB persistence and similarity query engine
├── frontend/
│   ├── app.py              # Main Streamlit application
│   └── components.py       # Minimalist UI components and custom CSS
├── config.py               # Application configuration and environment variables
├── requirements.txt        # Project dependencies
└── test_backend.py         # Automated backend test suite
```

## Getting Started

### 1. Prerequisites
- Python 3.10 or higher.

### 2. Installation

```bash
python -m venv .venv
# Activate virtual environment:
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Configuration

Create a .env file from .env.example:

```bash
cp .env.example .env
```

Configure your settings in .env:

```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-flash-preview
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=models/gemini-embedding-001
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K_RETRIEVAL=4
```

### 4. Running the Application

```bash
streamlit run frontend/app.py
```

The application will be available at http://localhost:8501.

## Testing

Run the automated test suite covering Data Layer and Backend components:

```bash
python test_backend.py
```
