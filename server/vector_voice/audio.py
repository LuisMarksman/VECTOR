"""Opus <-> PCM plumbing.

The ESP32 speaks Opus in both directions; every speech API we talk to speaks
raw PCM. This module is the translation layer, and it is the only place that
knows about libopus or ffmpeg.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import opuslib

log = logging.getLogger(__name__)


class OpusDecoder:
    """Device uplink: 16 kHz mono Opus frames -> PCM16 bytes."""

    def __init__(self, sample_rate: int, frame_samples: int) -> None:
        self._decoder = opuslib.Decoder(sample_rate, 1)
        self._frame_samples = frame_samples

    def decode(self, frame: bytes) -> bytes:
        try:
            return self._decoder.decode(frame, self._frame_samples)
        except opuslib.OpusError as exc:
            log.warning("opus decode failed (%s), emitting silence", exc)
            return b"\x00" * (self._frame_samples * 2)


class OpusEncoder:
    """Device downlink: PCM16 -> Opus frames of exactly frame_samples each.

    Feed it arbitrary-length PCM; it buffers and yields whole frames only,
    because the firmware's decoder is configured for a fixed frame size.
    """

    def __init__(self, sample_rate: int, frame_samples: int, bitrate: int = 24000) -> None:
        self._encoder = opuslib.Encoder(sample_rate, 1, opuslib.APPLICATION_AUDIO)
        try:
            self._encoder.bitrate = bitrate
        except Exception:  # pragma: no cover - older opuslib builds
            pass
        self._frame_samples = frame_samples
        self._frame_bytes = frame_samples * 2
        self._buf = bytearray()

    def push(self, pcm: bytes) -> list[bytes]:
        self._buf.extend(pcm)
        frames = []
        while len(self._buf) >= self._frame_bytes:
            chunk = bytes(self._buf[: self._frame_bytes])
            del self._buf[: self._frame_bytes]
            frames.append(self._encoder.encode(chunk, self._frame_samples))
        return frames

    def flush(self) -> list[bytes]:
        """Zero-pad whatever is left into one final frame."""
        if not self._buf:
            return []
        self._buf.extend(b"\x00" * (self._frame_bytes - len(self._buf)))
        chunk = bytes(self._buf[: self._frame_bytes])
        self._buf.clear()
        return [self._encoder.encode(chunk, self._frame_samples)]


async def decode_to_pcm(
    source: AsyncIterator[bytes],
    input_format: str,
    target_rate: int,
    ffmpeg_binary: str = "ffmpeg",
) -> AsyncIterator[bytes]:
    """Stream `source` through ffmpeg and yield mono PCM16 at `target_rate`.

    Streaming matters: TTS audio starts flowing out of here while the TTS
    engine is still generating, which is most of the perceived latency win.
    """
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel", "error",
        "-f", input_format,
        "-i", "pipe:0",
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", str(target_rate),
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def pump() -> None:
        try:
            async for chunk in source:
                proc.stdin.write(chunk)
                await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                proc.stdin.close()
                await proc.stdin.wait_closed()
            except (BrokenPipeError, ConnectionResetError, RuntimeError):
                pass

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk
    finally:
        pump_task.cancel()
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        stderr = await proc.stderr.read()
        await proc.wait()
        if proc.returncode not in (0, None) and stderr:
            log.debug("ffmpeg: %s", stderr.decode(errors="replace").strip())


async def resample_pcm(
    source: AsyncIterator[bytes],
    source_rate: int,
    target_rate: int,
    ffmpeg_binary: str = "ffmpeg",
) -> AsyncIterator[bytes]:
    """Resample raw PCM16 mono. Pass-through when the rates already match."""
    if source_rate == target_rate:
        async for chunk in source:
            yield chunk
        return
    async for chunk in _raw_pcm_ffmpeg(source, source_rate, target_rate, ffmpeg_binary):
        yield chunk


async def _raw_pcm_ffmpeg(
    source: AsyncIterator[bytes],
    source_rate: int,
    target_rate: int,
    ffmpeg_binary: str,
) -> AsyncIterator[bytes]:
    """decode_to_pcm cannot express raw-PCM input flags, so do it explicitly."""
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_binary,
        "-hide_banner", "-loglevel", "error",
        "-f", "s16le", "-ar", str(source_rate), "-ac", "1",
        "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(target_rate),
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    async def pump() -> None:
        try:
            async for chunk in source:
                proc.stdin.write(chunk)
                await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                proc.stdin.close()
                await proc.stdin.wait_closed()
            except (BrokenPipeError, ConnectionResetError, RuntimeError):
                pass

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk
    finally:
        pump_task.cancel()
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        await proc.wait()
