"""Unit tests for Phase 7 LLM Providers (OllamaProvider and MockProvider)."""

from backend.llm.provider import MockProvider, OllamaProvider


def test_mock_provider_generation():
    """Verify MockProvider returns valid JSON and telemetry."""
    provider = MockProvider(model="mock-qwen2.5:1.5b", default_decision="FOOD_SUBSIDY")
    assert provider.is_available() is True
    assert provider.model_name == "mock-qwen2.5:1.5b"

    raw_text, success, latency_ms = provider.generate("Test prompt")
    assert success is True
    assert latency_ms > 0.0
    assert "FOOD_SUBSIDY" in raw_text


def test_ollama_provider_offline_fallback():
    """Verify OllamaProvider gracefully returns failure if server is unreachable."""
    provider = OllamaProvider(
        base_url="http://127.0.0.1:59999",  # Port with no listener
        model="qwen2.5:1.5b",
        timeout_seconds=0.5,
    )
    assert provider.is_available() is False

    raw_text, success, latency_ms = provider.generate("Prompt")
    assert success is False
    assert raw_text == ""
    assert latency_ms == 0.0
    provider.close()


def test_ollama_provider_live_if_running():
    """Test live Ollama connection if daemon is currently running on localhost."""
    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:1.5b",
        timeout_seconds=20.0,
    )
    if provider.is_available():
        raw_text, success, latency_ms = provider.generate(
            'Return JSON: {"status": "ok"}', json_format=True
        )
        assert success is True
        assert latency_ms > 0.0
        assert "ok" in raw_text.lower()
    provider.close()
