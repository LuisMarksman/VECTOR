"""Pluggable language-model backends.

The agent talks to an :class:`LLMProvider`; the concrete backend is chosen at
runtime from configuration. The default ``mock`` backend needs no API key and
gives deterministic, offline-friendly behaviour so the whole stack runs (and is
testable) out of the box. Swap in ``anthropic`` or ``openai`` for real
reasoning by setting ``VECTOR_LLM_PROVIDER`` and the matching API key.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.config import Settings

logger = logging.getLogger("vector.llm")


class LLMProvider(Protocol):
    """Minimal chat-completion interface."""

    async def complete(self, system: str, prompt: str) -> str: ...


class MockLLM:
    """Deterministic, dependency-free backend for local dev and tests."""

    def __init__(self, model: str = "mock") -> None:
        self.model = model

    async def complete(self, system: str, prompt: str) -> str:  # noqa: ARG002
        text = prompt.strip()
        lowered = text.lower()
        if any(word in lowered for word in ("hello", "hi ", "hey")):
            return "Hello! I'm VECTOR. How can I help you today?"
        if lowered.endswith("?"):
            return f"That's a good question about '{text}'. I'll look into it."
        return f"Okay — {text}"


class AnthropicLLM:
    """Anthropic Claude backend (requires the ``anthropic`` extra + API key)."""

    def __init__(self, model: str) -> None:
        from anthropic import AsyncAnthropic  # lazy import

        self.model = model
        self._client = AsyncAnthropic()

    async def complete(self, system: str, prompt: str) -> str:
        resp = await self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")


class OpenAILLM:
    """OpenAI backend (requires the ``openai`` extra + API key)."""

    def __init__(self, model: str) -> None:
        from openai import AsyncOpenAI  # lazy import

        self.model = model
        self._client = AsyncOpenAI()

    async def complete(self, system: str, prompt: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""


def get_llm(settings: Settings) -> LLMProvider:
    """Instantiate the configured LLM backend, falling back to the mock."""
    provider = settings.llm_provider.lower()
    try:
        if provider == "anthropic":
            return AnthropicLLM(settings.llm_model)
        if provider == "openai":
            return OpenAILLM(settings.llm_model)
    except Exception as exc:  # missing key/lib — degrade rather than crash
        logger.warning("LLM provider '%s' unavailable (%s); using mock", provider, exc)
    if provider not in ("mock", "local"):
        logger.info("Unknown LLM provider '%s'; using mock", provider)
    return MockLLM(settings.llm_model)
