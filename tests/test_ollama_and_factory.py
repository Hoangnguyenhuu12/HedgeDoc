"""
Test Suite for Ollama Provider, Model Selection, and ProviderFactory.
"""

import pytest
from backend.providers.factory import ProviderFactory
from backend.providers.ollama_provider import OllamaLLM, OllamaEmbedding, check_ollama_status
from backend.providers.gemini_provider import GeminiLLM
from backend.rag_engine import RAGEngine


def test_provider_factory_available_models():
    """Verify available models for each supported provider."""
    gemini_models = ProviderFactory.get_available_models("gemini")
    assert "gemini-2.5-flash" in gemini_models
    assert len(gemini_models) >= 3

    openai_models = ProviderFactory.get_available_models("openai")
    assert "gpt-4o-mini" in openai_models

    ollama_models = ProviderFactory.get_available_models("ollama")
    assert "qwen2.5:7b" in ollama_models


def test_ollama_status_offline_graceful():
    """Verify check_ollama_status returns a structured dict without crashing when offline."""
    status = check_ollama_status(base_url="http://localhost:19999", timeout=0.5)
    assert isinstance(status, dict)
    assert status["online"] is False
    assert isinstance(status["models"], list)
    assert "Chưa khởi động" in status["message"] or "lỗi" in status["message"]


def test_ollama_llm_instantiation():
    """Verify OllamaLLM can be instantiated with custom parameters."""
    llm = ProviderFactory.get_llm(provider="ollama", model_name="qwen2.5:7b", temperature=0.1)
    assert isinstance(llm, OllamaLLM)
    assert llm.model_name == "qwen2.5:7b"
    assert llm.temperature == 0.1
    assert "11434" in llm.base_url


def test_ollama_embedding_instantiation():
    """Verify OllamaEmbedding can be instantiated via ProviderFactory."""
    embed = ProviderFactory.get_embedding(provider="ollama", model_name="nomic-embed-text")
    assert isinstance(embed, OllamaEmbedding)
    assert embed.model_name == "nomic-embed-text"


def test_rag_engine_dynamic_llm_switching():
    """Verify RAGEngine caches and switches LLM instances on demand."""
    engine = RAGEngine()
    
    # Default is gemini
    llm_gemini = engine.get_llm(provider="gemini", model_name="gemini-2.5-flash")
    assert isinstance(llm_gemini, GeminiLLM)
    assert llm_gemini.model_name == "gemini-2.5-flash"

    # Switch to Ollama
    llm_ollama = engine.get_llm(provider="ollama", model_name="qwen2.5:7b")
    assert isinstance(llm_ollama, OllamaLLM)
    assert llm_ollama.model_name == "qwen2.5:7b"

    # Switching back returns cached instance
    cached_gemini = engine.get_llm(provider="gemini", model_name="gemini-2.5-flash")
    assert cached_gemini is llm_gemini


def test_strip_and_stream_citations():
    """Verify inline citations are cleanly stripped both in full text and real-time token stream."""
    from backend.rag_engine import strip_inline_citations, clean_citation_stream

    raw_text = "Hoàng tử bé là nhân vật chính trong tác phẩm cùng tên của Antoine de Saint-Exupéry, được xuất bản năm 1943. [Source: 10048-hoang-tu-be-thuviensach.vn.pdf - Trang 6]"
    cleaned = strip_inline_citations(raw_text)
    assert cleaned == "Hoàng tử bé là nhân vật chính trong tác phẩm cùng tên của Antoine de Saint-Exupéry, được xuất bản năm 1943."

    # Test stream cleaner
    stream_chunks = [
        "Hoàng tử bé là nhân vật chính.",
        " [Source: 10048-hoang-tu-be.pdf - Trang 6]",
        " Được xuất bản năm 1943."
    ]
    stream_res = "".join(clean_citation_stream(stream_chunks)).strip()
    assert stream_res == "Hoàng tử bé là nhân vật chính. Được xuất bản năm 1943."
    assert "[Source" not in stream_res


if __name__ == "__main__":
    pytest.main(["-v", __file__])

