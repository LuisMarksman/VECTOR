"""Gemini text generation over the REST streaming endpoint.

Deliberately plain httpx rather than an SDK: the wire format is stable, there
is nothing to pin, and function calling stays visible as ordinary JSON for when
the MCP bridge lands.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator

import httpx

log = logging.getLogger(__name__)

# Split on sentence boundaries so TTS can start on sentence one while the model
# is still writing sentence two. Keeps the terminator attached.
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


class GeminiLLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        api_base: str = "https://generativelanguage.googleapis.com/v1beta",
        system_prompt: str = "",
        temperature: float = 0.7,
        max_output_tokens: int = 512,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._api_base = api_base.rstrip("/")
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _body(self, contents: list[dict[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_output_tokens,
            },
        }
        if self._system_prompt:
            body["systemInstruction"] = {"parts": [{"text": self._system_prompt}]}
        return body

    async def stream_sentences(self, contents: list[dict[str, Any]]) -> AsyncIterator[str]:
        """Yield complete sentences as they become available."""
        buffer = ""
        async for delta in self._stream_text(contents):
            buffer += delta
            while True:
                parts = _SENTENCE_END.split(buffer, maxsplit=1)
                if len(parts) == 1:
                    break
                sentence, buffer = parts[0].strip(), parts[1]
                if sentence:
                    yield sentence
        tail = buffer.strip()
        if tail:
            yield tail

    async def _stream_text(self, contents: list[dict[str, Any]]) -> AsyncIterator[str]:
        url = f"{self._api_base}/models/{self._model}:streamGenerateContent"
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        try:
            async with self._client.stream(
                "POST",
                url,
                params={"alt": "sse"},
                headers=headers,
                json=self._body(contents),
            ) as response:
                if response.status_code != 200:
                    detail = (await response.aread()).decode(errors="replace")
                    raise GeminiError(
                        f"Gemini returned {response.status_code}: {detail[:400]}"
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        log.debug("skipping unparseable SSE chunk: %r", payload[:120])
                        continue
                    for text in _extract_text(chunk):
                        yield text
        except httpx.HTTPError as exc:
            raise GeminiError(f"Gemini request failed: {exc}") from exc


def _extract_text(chunk: dict[str, Any]) -> list[str]:
    out = []
    for candidate in chunk.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if text:
                out.append(text)
    return out


class GeminiError(RuntimeError):
    pass


def build_contents(
    history: list[tuple[str, str]], user_text: str, max_turns: int
) -> list[dict[str, Any]]:
    """Turn (role, text) history into the Gemini `contents` array."""
    trimmed = history[-max_turns * 2 :] if max_turns > 0 else history
    contents = [{"role": role, "parts": [{"text": text}]} for role, text in trimmed]
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return contents
