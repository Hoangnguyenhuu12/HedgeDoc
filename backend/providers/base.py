"""
Standardized Abstract Interfaces (BaseLLM & BaseEmbedding).
Defines common behavior templates across AI providers without direct API calls.
"""

from abc import ABC, abstractmethod
from typing import List, Iterator, Optional


class BaseLLM(ABC):
    """
    Abstract interface for Large Language Models (LLM).
    Provides a provider-agnostic interface (Gemini, OpenAI, Anthropic, Ollama, etc.).
    """

    def __init__(self, model_name: str, temperature: float = 0.2):
        self.model_name = model_name
        self.temperature = temperature

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Synchronous generation.

        Args:
            prompt: User prompt and context sent to the model.
            system_instruction: System prompt controlling model behavior.

        Returns:
            Complete generated response text.
        """
        pass

    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Iterator[str]:
        """
        Streaming generation.

        Args:
            prompt: User prompt and context sent to the model.
            system_instruction: System prompt controlling model behavior.

        Returns:
            Iterator yielding stream tokens or chunks.
        """
        pass


class BaseEmbedding(ABC):
    """
    Abstract interface for vector embedding models.
    Ensures consistency across different embedding providers.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single piece of text into a vector representation.

        Args:
            text: Input text string.

        Returns:
            List of floats representing the embedding vector.
        """
        pass

    @abstractmethod
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 50
    ) -> List[List[float]]:
        """
        Batch-embed multiple text strings into a list of embedding vectors.
        Optimizes API calls and manages request rate limits.

        Args:
            texts: List of text strings.
            batch_size: Number of texts processed per API call.

        Returns:
            List of embedding vectors.
        """
        pass
