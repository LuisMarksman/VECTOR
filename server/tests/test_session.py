"""Pipeline tests that need no API keys and no hardware.

    cd server && python tests/test_session.py

Covers the parts that are expensive to debug against a real ESP32: the hello
handshake contract, Opus in both directions, turn message ordering, and the
playback pacing that keeps us inside the firmware's bounded decode queue.
"""

from __future__ import annotations

import asyncio
import math
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("GEMINI_API_KEY", "stub")
os.environ.setdefault("DEEPGRAM_API_KEY", "stub")

import opuslib  # noqa: E402

from vector_voice.config import Config  # noqa: E402
from vector_voice.session import Session  # noqa: E402

cfg = Config()
# main/audio/audio_service.h: MAX_DECODE_PACKETS_IN_QUEUE
FIRMWARE_QUEUE_LIMIT = 2400 // cfg.frame_duration_ms


def tone(rate: int, seconds: float, hz: int = 440, amp: int = 6000) -> bytes:
    n = int(rate * seconds)
    return struct.pack(
        "<%dh" % n, *[int(amp * math.sin(2 * math.pi * hz * i / rate)) for i in range(n)]
    )


class Recorder:
    def __init__(self) -> None:
        self.json_msgs: list[dict] = []
        self.audio: list[bytes] = []

    async def send_json(self, payload: dict) -> None:
        self.json_msgs.append(payload)

    async def send_bytes(self, payload: bytes) -> None:
        self.audio.append(payload)


class FakeTTS:
    def __init__(self, rate: int, seconds: float = 0.5) -> None:
        self.rate, self.seconds, self.calls = rate, seconds, []

    async def synthesize(self, text: str):
        self.calls.append(text)
        pcm = tone(self.rate, self.seconds)
        for i in range(0, len(pcm), 999):  # deliberately not frame-aligned
            yield pcm[i : i + 999]
            await asyncio.sleep(0)

    async def aclose(self) -> None:
        pass


class FakeLLM:
    def __init__(self, sentences: list[str]) -> None:
        self.sentences, self.contents = sentences, None

    async def stream_sentences(self, contents):
        self.contents = contents
        for sentence in self.sentences:
            await asyncio.sleep(0.01)
            yield sentence

    async def aclose(self) -> None:
        pass


def make_session(transport, sentences, tts_seconds=0.5):
    s = Session(transport, cfg)
    s._llm = FakeLLM(sentences)
    s._tts = FakeTTS(cfg.downlink_sample_rate, tts_seconds)
    return s


async def test_handshake() -> None:
    rec = Recorder()
    s = make_session(rec, ["hi."])
    await s.handle_json({
        "type": "hello", "version": 1, "transport": "websocket",
        "audio_params": {
            "format": "opus", "sample_rate": 16000,
            "channels": 1, "frame_duration": 60,
        },
    })
    hello = rec.json_msgs[0]
    # WebsocketProtocol::ParseServerHello rejects anything else.
    assert hello["type"] == "hello"
    assert hello["transport"] == "websocket"
    assert hello["session_id"]
    assert hello["audio_params"]["sample_rate"] == cfg.downlink_sample_rate
    assert hello["audio_params"]["frame_duration"] == cfg.frame_duration_ms
    print("PASS handshake")


async def test_uplink_decode() -> None:
    s = make_session(Recorder(), ["hi."])
    encoder = opuslib.Encoder(cfg.uplink_sample_rate, 1, opuslib.APPLICATION_VOIP)
    n = cfg.uplink_frame_samples
    frame = encoder.encode(tone(cfg.uplink_sample_rate, n / cfg.uplink_sample_rate, 300), n)

    fed: list[bytes] = []

    class StubSTT:
        async def send_audio(self, pcm):
            fed.append(pcm)

    s._stt, s._listening = StubSTT(), True
    await s.handle_audio(frame)
    assert len(fed) == 1 and len(fed[0]) == n * 2
    print(f"PASS uplink decode -> {len(fed[0])} bytes PCM16 @ {cfg.uplink_sample_rate}Hz")


async def test_turn_ordering_and_downlink() -> None:
    rec = Recorder()
    s = make_session(rec, ["Sure thing.", "The kitchen light is now on."])
    s._start_stt = lambda: asyncio.sleep(0)

    await s._on_utterance("turn on the kitchen light")
    await s._speak_task

    kinds = [(m.get("type"), m.get("state")) for m in rec.json_msgs]
    assert kinds[0] == ("stt", None), kinds
    assert kinds[-1] == ("tts", "stop"), kinds
    assert kinds.count(("tts", "sentence_start")) == 2, kinds
    assert kinds.index(("tts", "start")) < kinds.index(("tts", "sentence_start"))
    print("PASS turn ordering:", kinds)

    # Every downlink frame must decode at the rate we advertised.
    decoder = opuslib.Decoder(cfg.downlink_sample_rate, 1)
    fs = cfg.downlink_frame_samples
    for frame in rec.audio:
        assert len(decoder.decode(frame, fs)) == fs * 2
    dur = len(rec.audio) * cfg.frame_duration_ms / 1000
    print(f"PASS downlink: {len(rec.audio)} frames -> {dur:.2f}s, all decode cleanly")

    assert s._history == [
        ("user", "turn on the kitchen light"),
        ("model", "Sure thing. The kitchen light is now on."),
    ], s._history
    print("PASS history recorded")


async def test_pacing_within_firmware_queue() -> None:
    """Regression: the pacing budget is per turn, not per sentence. A reply made
    of many short sentences must not outrun MAX_DECODE_PACKETS_IN_QUEUE."""

    class Device:
        """Bounded queue draining at realtime, like AudioService."""

        def __init__(self) -> None:
            self.period = cfg.frame_duration_ms / 1000
            self.received = self.dropped = self.max_depth = 0
            self.t0 = None
            self.json_msgs: list[dict] = []

        async def send_json(self, payload):
            self.json_msgs.append(payload)

        async def send_bytes(self, payload):
            now = asyncio.get_event_loop().time()
            if self.t0 is None:
                self.t0 = now
            drained = int((now - self.t0) / self.period)
            depth = max(0, self.received - drained)
            if depth >= FIRMWARE_QUEUE_LIMIT:
                self.dropped += 1
            self.received += 1
            self.max_depth = max(self.max_depth, depth + 1)

    dev = Device()
    s = make_session(dev, [f"This is sentence number {i}." for i in range(10)], 0.45)
    s._start_stt = lambda: asyncio.sleep(0)

    t0 = asyncio.get_event_loop().time()
    await s._on_utterance("tell me a long story")
    await s._speak_task
    elapsed = asyncio.get_event_loop().time() - t0
    audio_sec = dev.received * cfg.frame_duration_ms / 1000

    print(f"   {dev.received} frames = {audio_sec:.1f}s audio sent in {elapsed:.1f}s; "
          f"peak queue {dev.max_depth}/{FIRMWARE_QUEUE_LIMIT}, dropped {dev.dropped}")
    assert dev.dropped == 0, f"device would drop {dev.dropped} frames"
    assert dev.max_depth <= FIRMWARE_QUEUE_LIMIT
    assert elapsed >= audio_sec * 0.75, "outran realtime"
    print("PASS pacing stays inside the firmware queue")


async def test_abort_stops_playback() -> None:
    rec = Recorder()
    s = make_session(rec, [f"Sentence {i} of a long reply." for i in range(10)])
    s._start_stt = lambda: asyncio.sleep(0)

    await s._on_utterance("hello")
    await asyncio.sleep(0.2)
    before = len(rec.audio)
    await s.handle_json({"type": "abort", "reason": "wake_word_detected"})
    await asyncio.sleep(0.5)
    after = len(rec.audio)
    assert after - before <= 2, f"playback continued after abort: {before} -> {after}"
    print(f"PASS abort halts playback ({before} -> {after} frames)")


async def main() -> None:
    for test in (
        test_handshake,
        test_uplink_decode,
        test_turn_ordering_and_downlink,
        test_pacing_within_firmware_queue,
        test_abort_stops_playback,
    ):
        await test()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
