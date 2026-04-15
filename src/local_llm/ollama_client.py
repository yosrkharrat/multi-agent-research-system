from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional

import ollama


@dataclass
class OllamaClient:
    """Small wrapper around the Ollama Python client with simple retries."""

    model: str = "llama3"
    host: str = "http://localhost:11434"
    timeout_s: float = 120.0
    retries: int = 3
    retry_backoff_s: float = 1.2

    def _client(self) -> ollama.Client:
        return ollama.Client(host=self.host, timeout=self.timeout_s)

    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("prompt must not be empty")

        selected_model = model or self.model
        last_err: Optional[Exception] = None

        for attempt in range(1, self.retries + 1):
            try:
                response = self._client().chat(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": temperature},
                    keep_alive="5m",
                )
                message = response.get("message", {})
                content = message.get("content", "")
                if not content:
                    raise RuntimeError("Ollama returned an empty completion")
                return content.strip()
            except Exception as exc:  # pragma: no cover - defensive runtime handling
                last_err = exc
                if attempt == self.retries:
                    break
                sleep_for = self.retry_backoff_s * attempt
                time.sleep(sleep_for)

        raise RuntimeError(
            f"Failed to generate completion with model '{selected_model}' after {self.retries} attempts"
        ) from last_err


def generate_text(prompt: str, model: str = "llama3") -> str:
    """Convenience helper for one-off prompts."""

    return OllamaClient(model=model).generate(prompt)
