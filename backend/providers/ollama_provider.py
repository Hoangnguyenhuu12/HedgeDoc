"""
Ollama Provider for Local LLM and Embeddings.
Enables offline, local inference via Ollama's HTTP REST API.
"""

import json
import logging
from typing import List, Iterator, Optional, Dict, Any
import requests
from config import config
from .base import BaseLLM, BaseEmbedding

logger = logging.getLogger(__name__)


def check_ollama_status(base_url: Optional[str] = None, timeout: float = 1.0) -> Dict[str, Any]:
    """
    Check if Ollama server is running and return available installed models.
    """
    url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
    try:
        resp = requests.get(f"{url}/api/tags", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
            return {
                "online": True,
                "models": models,
                "message": f"Ollama đang chạy ({len(models)} models có sẵn)."
            }
        return {
            "online": False,
            "models": [],
            "message": f"Ollama phản hồi mã lỗi {resp.status_code}."
        }
    except Exception as exc:
        return {
            "online": False,
            "models": [],
            "message": f"Chưa khởi động Ollama ({url})."
        }


class OllamaLLM(BaseLLM):
    """
    Local Large Language Model using Ollama REST API.
    Supports both synchronous and streaming generation.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        model = model_name or "qwen2.5:7b"
        temp = temperature if temperature is not None else config.LLM_TEMPERATURE
        super().__init__(model_name=model, temperature=temp)
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Synchronous generation via Ollama /api/chat.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=180
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Ollama trả về lỗi HTTP {resp.status_code}: {resp.text}"
                )
            result = resp.json()
            return result.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Không thể kết nối đến Ollama tại {self.base_url}. "
                f"Vui lòng khởi động Ollama (mở app hoặc chạy `ollama serve`)."
            )

    def stream_generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Iterator[str]:
        """
        Streaming generation via Ollama /api/chat with stream=True.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.temperature
            }
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=180
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Ollama trả về mã lỗi HTTP {resp.status_code}: {resp.text}"
                )

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Không thể kết nối đến Ollama tại {self.base_url}. "
                f"Vui lòng khởi động Ollama (mở app hoặc chạy `ollama serve`)."
            )


class OllamaEmbedding(BaseEmbedding):
    """
    Vector embedding provider using Ollama REST API.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        model = model_name or "nomic-embed-text"
        super().__init__(model_name=model)
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")

    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string using Ollama /api/embeddings.
        """
        payload = {
            "model": self.model_name,
            "prompt": text
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=60
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Ollama embedding lỗi HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json().get("embedding", [])
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Không thể kết nối đến Ollama tại {self.base_url}."
            )

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 50
    ) -> List[List[float]]:
        """
        Batch embed multiple text strings using Ollama /api/embed endpoint.
        Falls back to /api/embeddings if /api/embed is unavailable.
        """
        if not texts:
            return []

        cleaned_texts = [t.strip() if t.strip() else " " for t in texts]
        results: List[List[float]] = []

        try:
            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i + batch_size]
                payload = {
                    "model": self.model_name,
                    "input": batch
                }
                resp = requests.post(
                    f"{self.base_url}/api/embed",
                    json=payload,
                    timeout=120
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embs = data.get("embeddings", [])
                    if embs and len(embs) == len(batch):
                        results.extend(embs)
                        continue

                # Fallback for this batch
                for text in batch:
                    results.append(self.embed_text(text))
            return results
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Không thể kết nối đến Ollama tại {self.base_url}."
            )
        except Exception:
            # Sequential fallback
            results = []
            for text in cleaned_texts:
                results.append(self.embed_text(text))
            return results
