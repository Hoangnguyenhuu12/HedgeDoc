"""
Google Gemini API Adapter (Chat & Embedding).
Handles remote Google API communication with automated exponential backoff for 429 Rate Limits.
"""

import time
import warnings
from typing import List, Iterator, Optional

warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from .base import BaseLLM, BaseEmbedding


class GeminiLLM(BaseLLM):
    """
    Adapter integrating Google Gemini LLM via google.generativeai SDK.
    Supports synchronous text generation and real-time streaming tokens.
    """

    FALLBACK_MODELS = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    ]

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.2
    ):
        super().__init__(model_name=model_name, temperature=temperature)
        if not api_key:
            raise ValueError("GEMINI_API_KEY must not be empty when initializing GeminiLLM.")

        genai.configure(api_key=api_key)
        self.api_key = api_key
        self.exhausted_models = set()

    def _get_active_model_name(self) -> str:
        if self.model_name not in self.exhausted_models:
            return self.model_name
        for m in self.FALLBACK_MODELS:
            if m not in self.exhausted_models:
                return m
        return self.FALLBACK_MODELS[0]

    def _get_model(self, model_name: str, system_instruction: Optional[str] = None) -> genai.GenerativeModel:
        gen_config = GenerationConfig(
            temperature=self.temperature,
            top_p=0.95,
        )
        return genai.GenerativeModel(
            model_name=model_name,
            generation_config=gen_config,
            system_instruction=system_instruction
        )

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        active = self._get_active_model_name()
        candidates = [active] + [m for m in self.FALLBACK_MODELS if m not in self.exhausted_models and m != active]

        last_err = None
        for m_name in candidates:
            model = self._get_model(m_name, system_instruction=system_instruction)
            try:
                response = model.generate_content(prompt)
                return response.text if response.text else ""
            except Exception as e:
                last_err = e
                if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                    self.exhausted_models.add(m_name)
                    continue
                raise e

        if last_err:
            raise last_err
        return ""

    def stream_generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Iterator[str]:
        active = self._get_active_model_name()
        candidates = [active] + [m for m in self.FALLBACK_MODELS if m not in self.exhausted_models and m != active]

        response = None
        last_err = None
        for m_name in candidates:
            model = self._get_model(m_name, system_instruction=system_instruction)
            try:
                response = model.generate_content(prompt, stream=True)
                break
            except Exception as e:
                last_err = e
                if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                    self.exhausted_models.add(m_name)
                    continue
                raise e

        if response is None:
            if last_err:
                raise last_err
            return

        for chunk in response:
            try:
                if chunk.text:
                    yield chunk.text
            except Exception:
                continue


class GeminiEmbedding(BaseEmbedding):
    """
    Adapter integrating vector embedding models from Google Gemini.
    Supports automated batching, rate limit handling, and automatic model fallback.
    """

    FALLBACK_MODELS = [
        "models/gemini-embedding-2",
        "models/gemini-embedding-001",
        "models/gemini-embedding-2-preview"
    ]

    def __init__(
        self,
        api_key: str,
        model_name: str = "models/gemini-embedding-2"
    ):
        super().__init__(model_name=model_name)
        if not api_key:
            raise ValueError("GEMINI_API_KEY must not be empty when initializing GeminiEmbedding.")

        genai.configure(api_key=api_key)
        self.api_key = api_key
        self.exhausted_models = set()
        self._openai_fallback: Optional[BaseEmbedding] = None

    def _switch_fallback_model(self) -> bool:
        """Switch to an alternate embedding model without looping over already exhausted models."""
        self.exhausted_models.add(self.model_name)
        for candidate in self.FALLBACK_MODELS:
            if candidate not in self.exhausted_models:
                print(f"  [Auto-Fallback] Quota reached for '{self.model_name}'. Switching to '{candidate}'...", flush=True)
                self.model_name = candidate
                return True

        # If all Gemini models are exhausted, attempt fallback to OpenAI
        from config import config
        if config.OPENAI_API_KEY and not self._openai_fallback:
            try:
                from .openai_provider import OpenAIEmbedding
                print("  [Auto-Fallback] All Gemini embedding models exhausted. Switching to OpenAI (text-embedding-3-large)...", flush=True)
                self._openai_fallback = OpenAIEmbedding(
                    api_key=config.OPENAI_API_KEY,
                    model_name="text-embedding-3-large",
                    dimensions=3072
                )
                return True
            except Exception as e:
                print(f"  [Auto-Fallback] Could not initialize OpenAI fallback: {e}", flush=True)

        return False

    def embed_text(self, text: str) -> List[float]:
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        if self._openai_fallback:
            return self._openai_fallback.embed_text(cleaned_text)

        for attempt in range(5):
            try:
                response = genai.embed_content(
                    model=self.model_name,
                    content=cleaned_text
                )
                return response["embedding"]
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "resourceexhausted" in type(e).__name__.lower():
                    if "quota exceeded" in err_str or "embedcontentrequestsperday" in err_str:
                        if self._switch_fallback_model():
                            if self._openai_fallback:
                                return self._openai_fallback.embed_text(cleaned_text)
                            continue
                    wait_time = 10 * (attempt + 1)
                    print(f"  [Notice] Gemini Embedding rate limit (429). Waiting {wait_time}s before retry (Attempt {attempt+1}/5)...", flush=True)
                    time.sleep(wait_time)
                else:
                    raise e
        raise RuntimeError("Embedding request failed after 5 retries due to rate limits.")

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 40
    ) -> List[List[float]]:
        if not texts:
            return []

        if self._openai_fallback:
            return self._openai_fallback.embed_batch(texts, batch_size=batch_size)

        all_embeddings: List[List[float]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for b_idx, i in enumerate(range(0, len(texts), batch_size), start=1):
            batch = texts[i:i + batch_size]
            cleaned_batch = [t.strip() if t.strip() else " " for t in batch]

            success = False
            for attempt in range(5):
                try:
                    response = genai.embed_content(
                        model=self.model_name,
                        content=cleaned_batch
                    )
                    raw_embeddings = response.get("embedding", [])
                    if raw_embeddings and isinstance(raw_embeddings[0], list):
                        all_embeddings.extend(raw_embeddings)
                    else:
                        all_embeddings.append(raw_embeddings)
                    success = True
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "resourceexhausted" in type(e).__name__.lower():
                        if "quota exceeded" in err_str or "embedcontentrequestsperday" in err_str:
                            if self._switch_fallback_model():
                                if self._openai_fallback:
                                    remaining_texts = texts[i:]
                                    remaining_embeds = self._openai_fallback.embed_batch(remaining_texts, batch_size=batch_size)
                                    all_embeddings.extend(remaining_embeds)
                                    return all_embeddings
                                continue
                        wait_time = 10 * (attempt + 1)
                        print(f"  [Rate Limit 429] Batch {b_idx}/{total_batches} hit rate limit. Waiting {wait_time}s before retry (Attempt {attempt+1}/5)...", flush=True)
                        time.sleep(wait_time)
                    else:
                        raise e

            if not success:
                raise RuntimeError(f"Failed to generate embedding for batch {b_idx} after 5 attempts.")

            # Gentle pause between batches to respect RPM limits
            if i + batch_size < len(texts):
                time.sleep(1.0)

        return all_embeddings
