"""One conversation with one device.

Owns the turn state machine:

    device audio (Opus 16k)
        -> Opus decode -> PCM16 -> Deepgram
        -> utterance text -> Gemini (streamed by sentence)
        -> TTS -> PCM -> Opus encode 24k -> device

The firmware's default listening mode is kListeningModeAutoStop, so the device
streams continuously and *we* decide when the user's turn ended. Deepgram's
endpointing makes that call.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from . import protocol
from .audio import OpusDecoder, OpusEncoder
from .config import Config
from .providers.llm_gemini import GeminiError, GeminiLLM, build_contents
from .providers.stt_deepgram import DeepgramStream
from .providers.tts import build_tts

log = logging.getLogger(__name__)


class Transport:
    """Minimal duck-type over a FastAPI WebSocket so tests can substitute one."""

    async def send_json(self, payload: dict[str, Any]) -> None: ...
    async def send_bytes(self, payload: bytes) -> None: ...


class Session:
    def __init__(self, transport: Transport, cfg: Config, device_id: str = "") -> None:
        self.transport = transport
        self.cfg = cfg
        self.device_id = device_id
        self.session_id = uuid.uuid4().hex[:16]

        self._decoder = OpusDecoder(cfg.uplink_sample_rate, cfg.uplink_frame_samples)
        self._llm = GeminiLLM(
            cfg.gemini_api_key,
            cfg.gemini_model,
            api_base=cfg.gemini_api_base,
            system_prompt=cfg.system_prompt,
            temperature=cfg.gemini_temperature,
            max_output_tokens=cfg.gemini_max_output_tokens,
        )
        self._tts = build_tts(cfg)

        self._stt: DeepgramStream | None = None
        self._stt_spent = False
        self._history: list[tuple[str, str]] = []
        self._speak_task: asyncio.Task | None = None
        self._turn_lock = asyncio.Lock()
        self._listening = False
        self._closed = False
        # Ignore transcripts produced from audio the device sent before we
        # aborted -- otherwise a barge-in replays the interrupted utterance.
        self._turn_epoch = 0

    # -- lifecycle -------------------------------------------------------

    async def handle_hello(self, message: dict[str, Any]) -> None:
        audio = message.get("audio_params", {})
        log.info(
            "device hello: id=%s format=%s rate=%s frame=%sms features=%s",
            self.device_id,
            audio.get("format"),
            audio.get("sample_rate"),
            audio.get("frame_duration"),
            message.get("features", {}),
        )
        await self.transport.send_json(
            protocol.server_hello(
                self.session_id, self.cfg.downlink_sample_rate, self.cfg.frame_duration_ms
            )
        )
        if self.cfg.greeting:
            await self._speak_text(self.cfg.greeting, emotion="happy")

    async def close(self) -> None:
        self._closed = True
        await self._cancel_speaking()
        await self._stop_stt()
        await self._llm.aclose()
        await self._tts.aclose()

    # -- inbound ---------------------------------------------------------

    async def handle_audio(self, frame: bytes) -> None:
        """Binary Opus frame from the device."""
        if not self._listening or self._stt is None:
            return
        pcm = self._decoder.decode(frame)
        await self._stt.send_audio(pcm)

    async def handle_json(self, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "hello":
            await self.handle_hello(message)
        elif kind == "listen":
            await self._handle_listen(message)
        elif kind == "abort":
            log.info("device abort (reason=%s)", message.get("reason"))
            await self._cancel_speaking()
        elif kind == "mcp":
            # Device-side tool plumbing. Wired up in the next milestone; log so
            # the tool list is visible while developing.
            log.debug("mcp from device: %s", json.dumps(message.get("payload"))[:400])
        elif kind == "goodbye":
            await self._stop_stt()
        else:
            log.debug("unhandled message type %r", kind)

    async def _handle_listen(self, message: dict[str, Any]) -> None:
        state = message.get("state")
        if state == "start":
            log.info("listen start (mode=%s)", message.get("mode"))
            await self._start_stt()
        elif state == "stop":
            log.info("listen stop")
            await self._finish_stt()
        elif state == "detect":
            # Wake word fired on-device. The firmware may also have streamed the
            # wake-word audio just before this; treat the supplied text as the
            # start of the turn rather than a user question.
            wake_text = (message.get("text") or "").strip()
            log.info("wake word detected: %r", wake_text)
            await self._start_stt()

    # -- STT -------------------------------------------------------------

    async def _start_stt(self) -> None:
        if self._listening:
            return
        # Reuse a live stream across turns: a Deepgram connection handles many
        # utterances, and reconnecting per turn would add setup latency to
        # every single reply. Only a finished (CloseStream'd) one is unusable.
        if self._stt is not None and not self._stt_spent:
            self._listening = True
            return
        await self._stop_stt()
        self._stt = DeepgramStream(
            self.cfg.deepgram_api_key,
            model=self.cfg.deepgram_model,
            language=self.cfg.deepgram_language,
            sample_rate=self.cfg.uplink_sample_rate,
            endpointing_ms=self.cfg.deepgram_endpointing_ms,
            utterance_end_ms=self.cfg.deepgram_utterance_end_ms,
            on_utterance=self._on_utterance,
        )
        try:
            await self._stt.start()
            self._stt_spent = False
            self._listening = True
        except Exception as exc:
            log.exception("failed to open Deepgram stream")
            self._stt = None
            await self._alert("Speech error", str(exc)[:120])

    async def _finish_stt(self) -> None:
        """Device sent `listen stop` (manual mode, button released). CloseStream
        flushes and then terminates, so this stream cannot be reused."""
        if self._stt is not None:
            await self._stt.finish()
            self._stt_spent = True
        self._listening = False

    async def _stop_stt(self) -> None:
        self._listening = False
        if self._stt is not None:
            await self._stt.close()
            self._stt = None
        self._stt_spent = False

    async def _on_utterance(self, text: str) -> None:
        if self._closed or not text:
            return
        if self._speak_task is not None and not self._speak_task.done():
            # Trailing audio from the turn we are already answering. Dropping it
            # is right: a genuine interruption arrives as an `abort` instead.
            log.debug("ignoring utterance while replying: %r", text[:60])
            return
        epoch = self._turn_epoch
        log.info("user: %s", text)
        await self.transport.send_json(protocol.stt(self.session_id, text))
        # Stop feeding audio while we answer; the device stops uploading anyway
        # once it sees tts start.
        self._listening = False
        self._speak_task = asyncio.create_task(self._respond(text, epoch))

    # -- LLM + TTS -------------------------------------------------------

    async def _respond(self, user_text: str, epoch: int) -> None:
        async with self._turn_lock:
            if epoch != self._turn_epoch:
                return
            started = time.monotonic()
            spoken: list[str] = []
            opened = False
            playback = self._new_playback()
            try:
                contents = build_contents(self._history, user_text, self.cfg.history_turns)
                async for sentence in self._llm.stream_sentences(contents):
                    if epoch != self._turn_epoch:
                        break
                    if not opened:
                        log.info("first sentence in %.2fs", time.monotonic() - started)
                        await self.transport.send_json(protocol.tts_start(self.session_id))
                        await self.transport.send_json(
                            protocol.llm_emotion(self.session_id, "happy", "🙂")
                        )
                        opened = True
                    spoken.append(sentence)
                    await self._speak_sentence(sentence, epoch, playback)
                if opened:
                    await self._finish_playback(playback, epoch)
            except _Interrupted:
                log.debug("playback interrupted")
            except GeminiError as exc:
                log.error("%s", exc)
                if not opened:
                    await self.transport.send_json(protocol.tts_start(self.session_id))
                    opened = True
                try:
                    await self._speak_sentence(
                        "Sorry, I could not reach my language model.", epoch, playback
                    )
                    await self._finish_playback(playback, epoch)
                except _Interrupted:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("response failed")
            finally:
                if opened:
                    await self.transport.send_json(protocol.tts_stop(self.session_id))
                if spoken and epoch == self._turn_epoch:
                    reply = " ".join(spoken)
                    log.info("vector: %s", reply)
                    self._history.append(("user", user_text))
                    self._history.append(("model", reply))
                # Deliberately no re-arm here. On `tts stop` the firmware moves
                # to Listening (auto mode) and sends its own `listen start`
                # (application.cc: HandleTtsStop -> StartListeningAudio), or to
                # Idle (manual mode) where opening a mic stream would be wrong.
                self._speak_task = None

    async def _speak_text(self, text: str, emotion: str = "neutral") -> None:
        """One-shot utterance that does not involve the LLM (greetings, errors)."""
        epoch = self._turn_epoch
        await self.transport.send_json(protocol.tts_start(self.session_id))
        await self.transport.send_json(
            protocol.llm_emotion(self.session_id, protocol.clamp_emotion(emotion))
        )
        playback = self._new_playback()
        await self._speak_sentence(text, epoch, playback)
        await self._finish_playback(playback, epoch)
        await self.transport.send_json(protocol.tts_stop(self.session_id))

    def _new_playback(self) -> "_Playback":
        return _Playback(
            OpusEncoder(self.cfg.downlink_sample_rate, self.cfg.downlink_frame_samples),
            self.cfg.frame_duration_ms / 1000.0,
            self.cfg.playback_burst_frames,
        )

    async def _speak_sentence(
        self, sentence: str, epoch: int, playback: "_Playback"
    ) -> None:
        await self.transport.send_json(
            protocol.tts_sentence_start(self.session_id, sentence)
        )
        try:
            async for pcm in self._tts.synthesize(sentence):
                await self._emit(playback.encoder.push(pcm), epoch, playback)
        except _Interrupted:
            raise
        except Exception:
            log.exception("tts failed for %r", sentence[:60])

    async def _finish_playback(self, playback: "_Playback", epoch: int) -> None:
        """Flush the encoder's tail. Only at the very end of a turn -- flushing
        per sentence would zero-pad a gap into the middle of the reply."""
        try:
            await self._emit(playback.encoder.flush(), epoch, playback)
        except _Interrupted:
            pass

    async def _emit(
        self, frames: list[bytes], epoch: int, playback: "_Playback"
    ) -> None:
        for frame in frames:
            if epoch != self._turn_epoch:
                raise _Interrupted()
            await self.transport.send_bytes(frame)
            await playback.pace()

    async def _cancel_speaking(self) -> None:
        self._turn_epoch += 1
        task = self._speak_task
        self._speak_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async def _alert(self, status: str, message: str) -> None:
        await self.transport.send_json(
            protocol.alert(self.session_id, status, message)
        )


class _Interrupted(Exception):
    """Raised internally to unwind playback when a turn is aborted."""


class _Playback:
    """Opus encoder plus a rate limiter, scoped to one whole turn.

    The firmware's decode queue is MAX_DECODE_PACKETS_IN_QUEUE frames
    (2400 / frame_duration = 40 at 60 ms) and it silently drops the overflow.
    So we may run at most `burst_frames` of audio ahead of realtime -- and that
    budget is per *turn*, not per sentence, or a reply made of many short
    sentences would blow straight through it.

    Self-correcting: if TTS stalls, we fall behind realtime and stop sleeping
    until the lead is rebuilt.
    """

    def __init__(self, encoder: OpusEncoder, frame_period: float, burst_frames: int) -> None:
        self.encoder = encoder
        self._frame_period = frame_period
        self._max_lead = burst_frames * frame_period
        self._start: float | None = None
        self._scheduled = 0.0

    async def pace(self) -> None:
        now = time.monotonic()
        if self._start is None:
            self._start = now
        self._scheduled += self._frame_period
        lead = (self._start + self._scheduled) - now
        if lead > self._max_lead:
            await asyncio.sleep(lead - self._max_lead)
