"""
Provider Factory.
Instantiates LLM and Embedding objects based on configuration, enabling provider swapping without code modifications.
"""

from typing import Optional
from config import config
from .base import BaseLLM, BaseEmbedding
from .gemini_provider import GeminiLLM, GeminiEmbedding


class ProviderFactory:
    """
    Factory coordinating the instantiation of LLM and Embedding adapters.
    Enables pluggable providers without altering upper application layers.
    """

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
        else:
            raise ValueError(f"Embedding provider '{selected_provider}' is not supported.")
