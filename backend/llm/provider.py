"""HIVEMIND LLM Provider Abstraction Module."""

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx


class LLMProvider(ABC):
    """Abstract interface for local or remote LLM inference."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the active model."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is active and ready to accept inference requests."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_format: bool = True,
        temperature: float = 0.2,
    ) -> tuple[str, bool, float]:
        """
        Execute an inference request.
        Returns (response_text, is_success, latency_ms).
        """


class OllamaProvider(LLMProvider):
    """Local Ollama HTTP client implementation with health caching and timeout safety."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:1.5b",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._model = model
        self.timeout_seconds = timeout_seconds
        self._client: httpx.Client = httpx.Client(
            base_url=self.base_url, timeout=self.timeout_seconds
        )
        self._is_available: bool | None = None
        self._last_health_check: float = 0.0

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if local Ollama daemon is running and has the target model available."""
        now = time.monotonic()
        # Cache health check for 10 seconds to avoid per-tick network overhead
        if self._is_available is not None and (now - self._last_health_check) < 10.0:
            return self._is_available

        try:
            resp = self._client.get("/api/tags", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Match full tag (e.g. "qwen2.5:1.5b") or base name
                found = any(
                    self._model == m or self._model.split(":")[0] == m.split(":")[0]
                    for m in models
                )
                self._is_available = found
            else:
                self._is_available = False
        except (httpx.HTTPError, json.JSONDecodeError, Exception):  # noqa: BLE001
            self._is_available = False

        self._last_health_check = now
        return self._is_available

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_format: bool = True,
        temperature: float = 0.2,
    ) -> tuple[str, bool, float]:
        """Generate response from local Ollama model."""
        if not self.is_available():
            return ("", False, 0.0)

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_format:
            payload["format"] = "json"

        t0 = time.perf_counter()
        try:
            resp = self._client.post("/api/generate", json=payload)
            t1 = time.perf_counter()
            latency_ms = (t1 - t0) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                return (response_text, True, round(latency_ms, 2))
            else:
                return ("", False, round(latency_ms, 2))
        except (httpx.HTTPError, json.JSONDecodeError, Exception):  # noqa: BLE001
            t1 = time.perf_counter()
            return ("", False, round((t1 - t0) * 1000.0, 2))

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


class MockProvider(LLMProvider):
    """Deterministic mock provider for offline testing and reproducible test suites."""

    def __init__(
        self,
        model: str = "mock-qwen2.5:1.5b",
        default_decision: str = "FOOD_SUBSIDY",
        confidence: float = 0.90,
    ) -> None:
        self._model = model
        self.default_decision = default_decision
        self.confidence = confidence

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_format: bool = True,
        temperature: float = 0.2,
    ) -> tuple[str, bool, float]:
        """Return deterministic JSON response."""
        res_dict = {
            "action": self.default_decision,
            "confidence": self.confidence,
            "rationale": "Mock strategic assessment based on municipal telemetry.",
        }
        return (json.dumps(res_dict), True, 5.0)
