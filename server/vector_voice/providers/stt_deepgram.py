"""Deepgram streaming speech-to-text.

Talks the raw WebSocket API rather than the SDK: it is a stable documented wire
protocol, one less dependency to pin, and it behaves identically on arm64.

Turn-taking lives here. The firmware's default listening mode is
kListeningModeAutoStop, which means the device streams continuously and the
*server* decides when the user stopped talking. Deepgram's endpointing plus
UtteranceEnd events are what make that decision.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable
from urllib.parse import urlencode

import websockets
from websockets.asyncio.client import connect

log = logging.getLogger(__name__)

DEEPGRAM_WS = "wss://api.deepgram.com/v1/listen"


class DeepgramStream:
    """One live transcription stream, roughly one user turn.

    `on_utterance` fires with the complete user utterance once Deepgram decides
    speech has ended. `on_partial` fires with interim text (useful for showing
    something on the display early, and for barge-in detection).
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "nova-3",
        language: str = "multi",
        sample_rate: int = 16000,
        endpointing_ms: int = 400,
        utterance_end_ms: int = 1000,
        on_utterance: Callable[[str], Awaitable[None]] | None = None,
        on_partial: Callable[[str], Awaitable[None]] | None = None,
        on_speech_started: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._api_key = api_key
        self._params = {
            "model": model,
            "language": language,
            "encoding": "linear16",
            "sample_rate": str(sample_rate),
            "channels": "1",
            "interim_results": "true",
            "smart_format": "true",
            "punctuate": "true",
            "vad_events": "true",
            "endpointing": str(endpointing_ms),
            "utterance_end_ms": str(utterance_end_ms),
        }
        self.on_utterance = on_utterance
        self.on_partial = on_partial
        self.on_speech_started = on_speech_started

        self._ws: websockets.ClientConnection | None = None
        self._reader: asyncio.Task | None = None
        self._keepalive: asyncio.Task | None = None
        self._finals: list[str] = []
        self._closed = asyncio.Event()

    # -- lifecycle -------------------------------------------------------

    async def start(self) -> None:
        url = f"{DEEPGRAM_WS}?{urlencode(self._params)}"
        self._ws = await connect(
            url,
            additional_headers={"Authorization": f"Token {self._api_key}"},
            max_size=None,
            ping_interval=5,
            ping_timeout=20,
        )
        self._reader = asyncio.create_task(self._read_loop())
        self._keepalive = asyncio.create_task(self._keepalive_loop())
        log.info("deepgram stream opened (model=%s)", self._params["model"])

    async def send_audio(self, pcm: bytes) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.send(pcm)
        except websockets.ConnectionClosed:
            log.warning("deepgram closed the connection while sending audio")

    async def finish(self) -> None:
        """Ask Deepgram to flush any buffered audio and finalise."""
        if self._ws is None:
            return
        try:
            await self._ws.send(json.dumps({"type": "CloseStream"}))
        except websockets.ConnectionClosed:
            pass

    async def close(self) -> None:
        for task in (self._keepalive, self._reader):
            if task is not None:
                task.cancel()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover - best effort teardown
                pass
        self._ws = None
        self._closed.set()

    # -- internals -------------------------------------------------------

    async def _keepalive_loop(self) -> None:
        """Deepgram drops idle sockets after ~10 s of no audio."""
        try:
            while True:
                await asyncio.sleep(5)
                if self._ws is not None:
                    await self._ws.send(json.dumps({"type": "KeepAlive"}))
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    continue
                await self._handle(json.loads(raw))
        except asyncio.CancelledError:
            raise
        except websockets.ConnectionClosed:
            log.debug("deepgram read loop closed")
        except Exception:
            log.exception("deepgram read loop failed")
        finally:
            self._closed.set()

    async def _handle(self, msg: dict) -> None:
        kind = msg.get("type")

        if kind == "SpeechStarted":
            if self.on_speech_started:
                await self.on_speech_started()
            return

        if kind == "UtteranceEnd":
            # Safety net: fires even when speech_final never arrives (e.g. the
            # user trails off without a clean endpoint).
            await self._emit()
            return

        if kind == "Results":
            alternatives = msg.get("channel", {}).get("alternatives", [])
            if not alternatives:
                return
            transcript = (alternatives[0].get("transcript") or "").strip()
            if not transcript:
                return

            if msg.get("is_final"):
                self._finals.append(transcript)
                if msg.get("speech_final"):
                    await self._emit()
            elif self.on_partial:
                interim = " ".join(self._finals + [transcript]).strip()
                await self.on_partial(interim)
            return

        if kind == "Error" or msg.get("error"):
            log.error("deepgram error: %s", msg)

    async def _emit(self) -> None:
        if not self._finals:
            return
        text = " ".join(self._finals).strip()
        self._finals.clear()
        if text and self.on_utterance:
            await self.on_utterance(text)
