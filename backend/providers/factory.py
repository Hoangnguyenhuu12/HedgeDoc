"""
Provider Factory.
Instantiates LLM and Embedding objects based on configuration, enabling provider swapping without code modifications.
"""

from typing import Optional, List, Dict, Any
from config import config
from .base import BaseLLM, BaseEmbedding
from .gemini_provider import GeminiLLM, GeminiEmbedding
from .ollama_provider import OllamaLLM, OllamaEmbedding, check_ollama_status


class ProviderFactory:
    """
    Factory coordinating the instantiation of LLM and Embedding adapters.
    Enables pluggable providers without altering upper application layers.
    """

    DEFAULT_MODELS: Dict[str, List[str]] = {
        "gemini": [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ],
        "openai": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ],
        "ollama": [
            "qwen2.5:7b",
            "llama3.1:8b",
            "deepseek-r1:8b",
            "qwen2.5:3b",
            "mistral:7b"
        ]
    }

    @classmethod
    def get_available_models(cls, provider: str) -> List[str]:
        """
        Return the list of suggested or locally discovered models for a given provider.
        """
        p = provider.lower()
        if p == "ollama":
            status = check_ollama_status()
            if status["online"] and status["models"]:
                return status["models"]
            return cls.DEFAULT_MODELS.get("ollama", [])
        return cls.DEFAULT_MODELS.get(p, [])

    @staticmethod
    def get_llm(
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> BaseLLM:
        selected_provider = (provider or config.LLM_PROVIDER).lower()
        selected_model = model_name or config.LLM_MODEL
        selected_temp = temperature if temperature is not None else config.LLM_TEMPERATURE

        if selected_provider == "gemini":
            return GeminiLLM(
                api_key=config.GEMINI_API_KEY,
                model_name=selected_model,
                temperature=selected_temp
            )
        elif selected_provider == "openai":
            try:
                from .openai_provider import OpenAILLM
                return OpenAILLM(
                    api_key=config.OPENAI_API_KEY,
                    model_name=selected_model,
                    temperature=selected_temp
                )
            except ImportError:
                raise ImportError(
                    "The 'openai' package is not installed. Please run: pip install openai"
                )
        elif selected_provider == "ollama":
            return OllamaLLM(
                model_name=selected_model,
                base_url=config.OLLAMA_BASE_URL,
                temperature=selected_temp
            )
        else:
            raise ValueError(f"LLM provider '{selected_provider}' is not supported.")

    @staticmethod
    def get_embedding(
        provider: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> BaseEmbedding:
        selected_provider = (provider or config.EMBEDDING_PROVIDER).lower()
        selected_model = model_name or config.EMBEDDING_MODEL

        if selected_provider == "gemini":
            return GeminiEmbedding(
                api_key=config.GEMINI_API_KEY,
                model_name=selected_model
            )
        elif selected_provider == "openai":
            try:
                from .openai_provider import OpenAIEmbedding
                return OpenAIEmbedding(
                    api_key=config.OPENAI_API_KEY,
                    model_name=selected_model
                )
            except ImportError:
                raise ImportError(
                    "The 'openai' package is not installed. Please run: pip install openai"
                )
        elif selected_provider == "ollama":
            return OllamaEmbedding(
                model_name=selected_model,
                base_url=config.OLLAMA_BASE_URL
            )
        else:
            raise ValueError(f"Embedding provider '{selected_provider}' is not supported.")
