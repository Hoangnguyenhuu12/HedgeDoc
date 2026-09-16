"""
Global Configuration Center (Single Source of Truth).
Loads environment variables from .env and supplies parameters system-wide without business logic.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load configuration from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class AppConfig:
    """Centralized configuration for HedgeDoc."""

    # Project directories
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    VECTOR_STORE_DIR: Path = BASE_DIR / "data" / "vector_store"
    RAW_DOCS_DIR: Path = BASE_DIR / "data" / "raw_docs"

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Provider & Model Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")

    # Vector DB & Retrieval Settings
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "hedgedoc_knowledge_base")
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "4"))

    # Chunking Strategy
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    def ensure_directories(self) -> None:
        """Ensure all required application data directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)


config = AppConfig()
config.ensure_directories()
