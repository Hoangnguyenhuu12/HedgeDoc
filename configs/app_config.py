"""
Central Configuration for the HedgeDoc Integration Application.
Loads settings from .env and environment variables.
"""

from pathlib import Path
import os
from typing import Optional
from dotenv import load_dotenv

# Base paths
HEDGEDOC_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = HEDGEDOC_DIR.parent

# Load environment
env_file = HEDGEDOC_DIR / ".env" if (HEDGEDOC_DIR / ".env").exists() else WORKSPACE_ROOT / ".env"
load_dotenv(env_file)


class AppConfig:
    def __init__(self):
        self.reload()

    def reload(self):
        env_f = HEDGEDOC_DIR / ".env" if (HEDGEDOC_DIR / ".env").exists() else WORKSPACE_ROOT / ".env"
        load_dotenv(env_f, override=True)

        # Paths encapsulated inside HedgeDoc
        self.DATA_DIR = HEDGEDOC_DIR / "data"
        self.RAW_DOCS_DIR = self.DATA_DIR / "raw_docs"
        self.PROCESSED_DIR = self.DATA_DIR / "processed"
        self.CHROMA_DIR = self.DATA_DIR / "chroma_db"

        self.RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        # Service endpoints (Optional remote REST service URLs)
        self.QUALITY_GATE_API_URL: Optional[str] = os.getenv("QUALITY_GATE_API_URL")
        self.OCR_ENGINE_API_URL: Optional[str] = os.getenv("OCR_ENGINE_API_URL")
        self.RAG_ENGINE_API_URL: Optional[str] = os.getenv("RAG_ENGINE_API_URL")

        # LLM & Embedding Settings
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
        self.EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama")
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-m3")

        # Retrieval Settings
        self.TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "4"))
        self.USE_HYBRID_SEARCH: bool = os.getenv("USE_HYBRID_SEARCH", "true").lower() == "true"
        self.HYBRID_DENSE_WEIGHT: float = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.6"))

        # Quality Gate Thresholds
        self.QUALITY_REJECT_THRESHOLD: float = float(os.getenv("QUALITY_REJECT_THRESHOLD", "2.0"))
        self.QUALITY_ENHANCE_THRESHOLD: float = float(os.getenv("QUALITY_ENHANCE_THRESHOLD", "3.2"))


config = AppConfig()
