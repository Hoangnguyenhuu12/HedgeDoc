"""
Google Gemini API Adapter (Chat & Embedding).
Handles remote Google API communication with automated exponential backoff for 429 Rate Limits.
"""

import time
from typing import List, Iterator, Optional
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from .base import BaseLLM, BaseEmbedding


class GeminiLLM(BaseLLM):
    """
    Adapter integrating Google Gemini LLM via google.generativeai SDK.
    Supports synchronous text generation and real-time streaming tokens.
    """

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

    def _get_model(self, system_instruction: Optional[str] = None) -> genai.GenerativeModel:
        gen_config = GenerationConfig(
            temperature=self.temperature,
            top_p=0.95,
        )
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=gen_config,
            system_instruction=system_instruction
        )

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        model = self._get_model(system_instruction=system_instruction)
        for attempt in range(4):
            try:
                response = model.generate_content(prompt)
                return response.text if response.text else ""
            except Exception as e:
                if ("429" in str(e) or "ResourceExhausted" in type(e).__name__) and attempt < 3:
                    wait_time = 10 * (attempt + 1)
                    time.sleep(wait_time)
                else:
                    raise e
        return ""

    def stream_generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Iterator[str]:
        model = self._get_model(system_instruction=system_instruction)
        response = None
        for attempt in range(4):
            try:
                response = model.generate_content(prompt, stream=True)
                break
            except Exception as e:
                if ("429" in str(e) or "ResourceExhausted" in type(e).__name__) and attempt < 3:
                    wait_time = 10 * (attempt + 1)
                    time.sleep(wait_time)
                else:
                    raise e

        if response is None:
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
    Supports automated batching to optimize throughput and handle rate limits.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "models/gemini-embedding-001"
    ):
        super().__init__(model_name=model_name)
        if not api_key:
            raise ValueError("GEMINI_API_KEY must not be empty when initializing GeminiEmbedding.")

        genai.configure(api_key=api_key)
        self.api_key = api_key

    def embed_text(self, text: str) -> List[float]:
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        for attempt in range(5):
            try:
                response = genai.embed_content(
                    model=self.model_name,
                    content=cleaned_text
                )
                return response["embedding"]
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                    wait_time = 15 * (attempt + 1)
                    print(f"  [Notice] Gemini Embedding reached rate limit (429). Waiting {wait_time}s before retry (Attempt {attempt+1}/5)...")
                    time.sleep(wait_time)
                else:
                    raise e
        raise RuntimeError("Embedding request failed after 5 retries due to rate limits.")

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 90
    ) -> List[List[float]]:
        if not texts:
            return []

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
                    if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                        wait_time = 25 * (attempt + 1)
                        print(f"  [Rate Limit 429] Batch {b_idx}/{total_batches} hit quota limit. Waiting {wait_time}s before retry (Attempt {attempt+1}/5)...")
                        time.sleep(wait_time)
                    else:
                        raise e

            if not success:
                raise RuntimeError(f"Failed to generate embedding for batch {b_idx} after 5 attempts.")

            # Short pause between batches to protect request rate limits (RPM)
            if i + batch_size < len(texts):
                time.sleep(1.5)

        return all_embeddings
