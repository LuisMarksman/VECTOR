"""Text-to-speech providers.

Every provider yields raw PCM16 mono at the server's downlink sample rate, so
the session layer only ever sees one shape of data and swapping engines is a
config change.

  edge   - Microsoft Edge read-aloud voices. Free, no signup, no key, genuinely
           good neural quality, and it streams. The default.
           Unofficial, so treat it as best-effort.
  gemini - Costs credits, returns PCM directly (no ffmpeg hop), takes
           natural-language style direction -- but it is NOT streaming and it
           is slow. Measured July 2026 on gemini-2.5-flash-preview-tts:
           1.9 s to synthesise "Yes." and 3.1 s for a short sentence.
           gemini-3.1-flash-tts-preview was worse (2.7 s / 9.2 s). That is a
           per-request floor you cannot hide behind sentence pipelining, so
           this is for pre-generated audio, not conversation.
  piper  - Fully local. No network, no cost, runs fine on a Pi 5. The offline
           fallback and the thing to use if the Edge endpoint ever dies.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import AsyncIterator, Protocol

import httpx

from ..audio import decode_to_pcm, resample_pcm

log = logging.getLogger(__name__)


class TTSProvider(Protocol):
    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Yield PCM16 mono at the configured sample rate."""
        ...

    async def aclose(self) -> None: ...


class EdgeTTS:
    def __init__(
        self,
        voice: str,
        sample_rate: int,
        *,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        ffmpeg_binary: str = "ffmpeg",
    ) -> None:
        self._voice = voice
        self._sample_rate = sample_rate
        self._rate = rate
        self._pitch = pitch
        self._ffmpeg = ffmpeg_binary

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        import edge_tts  # imported lazily so the other providers work without it

        communicate = edge_tts.Communicate(
            text, self._voice, rate=self._rate, pitch=self._pitch
        )

        async def mp3_chunks() -> AsyncIterator[bytes]:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        async for pcm in decode_to_pcm(
            mp3_chunks(), "mp3", self._sample_rate, self._ffmpeg
        ):
            yield pcm

    async def aclose(self) -> None:
        return None


class GeminiTTS:
    """Returns base64 PCM16 @ 24 kHz in a single response -- there is no partial
    output, so nothing can be played until the whole sentence is synthesised.
    See the module docstring for measured latency; it is too slow to converse
    with. Kept because it is the right tool for style-directed or
    pre-generated audio."""

    NATIVE_RATE = 24000

    def __init__(
        self,
        api_key: str,
        model: str,
        voice: str,
        sample_rate: int,
        *,
        api_base: str = "https://generativelanguage.googleapis.com/v1beta",
        ffmpeg_binary: str = "ffmpeg",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._sample_rate = sample_rate
        self._api_base = api_base.rstrip("/")
        self._ffmpeg = ffmpeg_binary
        self._client = httpx.AsyncClient(timeout=timeout)

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        url = f"{self._api_base}/models/{self._model}:generateContent"
        body = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self._voice}
                    }
                },
            },
        }
        response = await self._client.post(
            url,
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            json=body,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini TTS returned {response.status_code}: {response.text[:400]}"
            )
        data = response.json()
        pcm = b""
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    pcm += base64.b64decode(inline["data"])
        if not pcm:
            log.warning("Gemini TTS returned no audio for %r", text[:60])
            return

        async def once() -> AsyncIterator[bytes]:
            yield pcm

        async for chunk in resample_pcm(
            once(), self.NATIVE_RATE, self._sample_rate, self._ffmpeg
        ):
            yield chunk

    async def aclose(self) -> None:
        await self._client.aclose()


class PiperTTS:
    """Local neural TTS. `piper --model voice.onnx --output-raw` streams PCM on
    stdout at the model's native rate."""

    def __init__(
        self,
        binary: str,
        model_path: str,
        model_sample_rate: int,
        sample_rate: int,
        *,
        ffmpeg_binary: str = "ffmpeg",
    ) -> None:
        self._binary = binary
        self._model_path = model_path
        self._model_rate = model_sample_rate
        self._sample_rate = sample_rate
        self._ffmpeg = ffmpeg_binary

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        proc = await asyncio.create_subprocess_exec(
            self._binary,
            "--model", self._model_path,
            "--output-raw",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        proc.stdin.write(text.encode("utf-8") + b"\n")
        await proc.stdin.drain()
        proc.stdin.close()

        async def raw() -> AsyncIterator[bytes]:
            while True:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
            await proc.wait()

        async for chunk in resample_pcm(
            raw(), self._model_rate, self._sample_rate, self._ffmpeg
        ):
            yield chunk

    async def aclose(self) -> None:
        return None


def build_tts(cfg) -> TTSProvider:
    provider = cfg.tts_provider.lower()
    if provider == "edge":
        return EdgeTTS(
            cfg.edge_tts_voice,
            cfg.downlink_sample_rate,
            rate=cfg.edge_tts_rate,
            pitch=cfg.edge_tts_pitch,
            ffmpeg_binary=cfg.ffmpeg_binary,
        )
    if provider == "gemini":
        return GeminiTTS(
            cfg.gemini_api_key,
            cfg.gemini_tts_model,
            cfg.gemini_tts_voice,
            cfg.downlink_sample_rate,
            api_base=cfg.gemini_api_base,
            ffmpeg_binary=cfg.ffmpeg_binary,
        )
    if provider == "piper":
        return PiperTTS(
            cfg.piper_binary,
            cfg.piper_model,
            cfg.piper_sample_rate,
            cfg.downlink_sample_rate,
            ffmpeg_binary=cfg.ffmpeg_binary,
        )
    raise ValueError(f"Unknown TTS_PROVIDER: {cfg.tts_provider!r} (edge|gemini|piper)")
