"""
Global Configuration Center (Single Source of Truth).
Loads environment variables from .env and supplies parameters system-wide without business logic.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


class AppConfig:
    """Centralized configuration for HedgeDoc with hot-reload capability."""

    def __init__(self):
        # 1. Project directories
        self.BASE_DIR: Path = BASE_DIR
        self.DATA_DIR: Path = BASE_DIR / "data"
        self.VECTOR_STORE_DIR: Path = self.DATA_DIR / "vector_store"
        self.RAW_DOCS_DIR: Path = self.DATA_DIR / "raw_docs"

        # 2. Load settings from .env
        self.reload()
        self.ensure_directories()

    def reload(self) -> None:
        """Load or refresh all configuration values directly from .env."""
        load_dotenv(self.BASE_DIR / ".env", override=True)

        # API Keys
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

        # LLM Provider & Settings
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # Embedding Provider & Settings
        self.EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

        # Vector DB & Retrieval
        self.CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "hedgedoc_local_kb")
        self.TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "4"))

        # Chunking Strategy
        self.CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
        self.CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    def ensure_directories(self) -> None:
        """Ensure all required application data directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)


config = AppConfig()
