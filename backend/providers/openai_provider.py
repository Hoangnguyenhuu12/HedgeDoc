"""
OpenAI API Adapter (Chat & Embedding).
Implements BaseLLM and BaseEmbedding via HTTPX, compatible with OpenAI GPT and Embedding endpoints.
"""

import json
import time
from typing import List, Iterator, Optional
import httpx
from .base import BaseLLM, BaseEmbedding


class OpenAILLM(BaseLLM):
    """
    Adapter integrating OpenAI Chat Completions API (GPT-4o, GPT-4o-mini, etc.).
    Supports synchronous text generation and real-time streaming tokens.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.2
    ):
        super().__init__(model_name=model_name, temperature=temperature)
        if not api_key:
            raise ValueError("OPENAI_API_KEY must not be empty when initializing OpenAILLM.")
        self.api_key = api_key
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_messages(self, prompt: str, system_instruction: Optional[str] = None) -> List[dict]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        payload = {
            "model": self.model_name,
            "messages": self._build_messages(prompt, system_instruction),
            "temperature": self.temperature
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(self.endpoint, headers=self.headers, json=payload)
            data = resp.json()
            if resp.status_code != 200:
                err_msg = data.get("error", {}).get("message", resp.text)
                raise RuntimeError(f"OpenAI LLM error ({resp.status_code}): {err_msg}")
            return data["choices"][0]["message"]["content"]

    def stream_generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Iterator[str]:
        payload = {
            "model": self.model_name,
            "messages": self._build_messages(prompt, system_instruction),
            "temperature": self.temperature,
            "stream": True
        }
        with httpx.Client(timeout=60.0) as client:
            with client.stream("POST", self.endpoint, headers=self.headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = response.read().decode("utf-8")
                    raise RuntimeError(f"OpenAI Streaming error ({response.status_code}): {error_text}")
                for line in response.iter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            continue


class OpenAIEmbedding(BaseEmbedding):
    """
    Adapter integrating OpenAI Vector Embedding API (text-embedding-3-large, text-embedding-3-small).
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-large",
        dimensions: Optional[int] = 3072
    ):
        super().__init__(model_name=model_name)
        if not api_key:
            raise ValueError("OPENAI_API_KEY must not be empty when initializing OpenAIEmbedding.")
        self.api_key = api_key
        self.dimensions = dimensions
        self.endpoint = "https://api.openai.com/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def embed_text(self, text: str) -> List[float]:
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        payload = {
            "model": self.model_name,
            "input": cleaned_text
        }
        if "text-embedding-3" in self.model_name and self.dimensions:
            payload["dimensions"] = self.dimensions

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(self.endpoint, headers=self.headers, json=payload)
            data = resp.json()
            if resp.status_code != 200:
                err_msg = data.get("error", {}).get("message", resp.text)
                raise RuntimeError(f"OpenAI Embedding error ({resp.status_code}): {err_msg}")
            return data["data"][0]["embedding"]

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 50
    ) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            cleaned_batch = [t.strip() if t.strip() else " " for t in batch]

            payload = {
                "model": self.model_name,
                "input": cleaned_batch
            }
            if "text-embedding-3" in self.model_name and self.dimensions:
                payload["dimensions"] = self.dimensions

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(self.endpoint, headers=self.headers, json=payload)
                data = resp.json()
                if resp.status_code != 200:
                    err_msg = data.get("error", {}).get("message", resp.text)
                    raise RuntimeError(f"OpenAI Batch Embedding error ({resp.status_code}): {err_msg}")
                batch_embeds = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeds)

            if i + batch_size < len(texts):
                time.sleep(0.2)

        return all_embeddings
