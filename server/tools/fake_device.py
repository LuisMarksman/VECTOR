#!/usr/bin/env python3
"""Pretend to be the ESP32 so you can test the whole pipeline with no hardware.

It does exactly what the firmware does: hello handshake, listen start, stream
16 kHz Opus, then decode whatever comes back and write it to a WAV file.

    # speak a wav file at the server (any sample rate, it gets converted)
    python tools/fake_device.py --url ws://127.0.0.1:8000/xiaozhi/v1/ --wav question.wav

    # or just send silence to check the handshake
    python tools/fake_device.py --url ws://127.0.0.1:8000/xiaozhi/v1/ --seconds 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import wave

import opuslib
import websockets
from websockets.asyncio.client import connect

UPLINK_RATE = 16000
FRAME_MS = 60
FRAME_SAMPLES = UPLINK_RATE // 1000 * FRAME_MS


def wav_to_pcm16k(path: str) -> bytes:
    """Anything ffmpeg can read -> 16 kHz mono PCM16."""
    return subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", path,
            "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(UPLINK_RATE),
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    ).stdout


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8000/xiaozhi/v1/")
    parser.add_argument("--wav", help="audio file to send as the user's speech")
    parser.add_argument("--seconds", type=float, default=2.0, help="silence if no --wav")
    parser.add_argument("--out", default="reply.wav", help="where to write the reply")
    parser.add_argument("--token", default="", help="Authorization bearer token")
    parser.add_argument("--device-id", default="aa:bb:cc:dd:ee:ff")
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    if args.wav:
        pcm = wav_to_pcm16k(args.wav)
    else:
        pcm = b"\x00" * int(UPLINK_RATE * args.seconds) * 2

    headers = {
        "Device-Id": args.device_id,
        "Client-Id": "00000000-0000-0000-0000-000000000001",
        "Protocol-Version": "1",
    }
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    encoder = opuslib.Encoder(UPLINK_RATE, 1, opuslib.APPLICATION_VOIP)
    reply_pcm = bytearray()
    reply_rate = 24000
    decoder: opuslib.Decoder | None = None
    got_tts_stop = asyncio.Event()

    async with connect(args.url, additional_headers=headers, max_size=None) as ws:
        await ws.send(json.dumps({
            "type": "hello",
            "version": 1,
            "features": {"mcp": True},
            "transport": "websocket",
            "audio_params": {
                "format": "opus",
                "sample_rate": UPLINK_RATE,
                "channels": 1,
                "frame_duration": FRAME_MS,
            },
        }))

        async def reader() -> None:
            nonlocal decoder, reply_rate
            async for raw in ws:
                if isinstance(raw, bytes):
                    if decoder is None:
                        decoder = opuslib.Decoder(reply_rate, 1)
                    frame_samples = reply_rate // 1000 * FRAME_MS
                    try:
                        reply_pcm.extend(decoder.decode(raw, frame_samples))
                    except opuslib.OpusError as exc:
                        print(f"  ! opus decode error: {exc}", file=sys.stderr)
                    continue
                msg = json.loads(raw)
                kind = msg.get("type")
                if kind == "hello":
                    params = msg.get("audio_params", {})
                    reply_rate = params.get("sample_rate", 24000)
                    print(f"< hello  session={msg.get('session_id')} "
                          f"downlink={reply_rate}Hz/{params.get('frame_duration')}ms")
                elif kind == "stt":
                    print(f"< stt    {msg.get('text')!r}")
                elif kind == "tts":
                    state = msg.get("state")
                    if state == "sentence_start":
                        print(f"< speak  {msg.get('text')!r}")
                    else:
                        print(f"< tts    {state}")
                    if state == "stop":
                        got_tts_stop.set()
                elif kind == "llm":
                    print(f"< llm    emotion={msg.get('emotion')}")
                else:
                    print(f"< {kind:6} {json.dumps(msg)[:160]}")

        read_task = asyncio.create_task(reader())
        await asyncio.sleep(0.5)

        await ws.send(json.dumps({"type": "listen", "state": "start", "mode": "auto"}))
        print(f"> streaming {len(pcm) / 2 / UPLINK_RATE:.1f}s of audio")

        frame_bytes = FRAME_SAMPLES * 2
        for offset in range(0, len(pcm) - frame_bytes + 1, frame_bytes):
            chunk = pcm[offset : offset + frame_bytes]
            await ws.send(encoder.encode(chunk, FRAME_SAMPLES))
            await asyncio.sleep(FRAME_MS / 1000.0)  # realtime, like the device

        # Trailing silence so Deepgram's endpointing fires.
        silence = b"\x00" * frame_bytes
        for _ in range(int(1500 / FRAME_MS)):
            await ws.send(encoder.encode(silence, FRAME_SAMPLES))
            await asyncio.sleep(FRAME_MS / 1000.0)

        await ws.send(json.dumps({"type": "listen", "state": "stop"}))
        print("> listen stop, waiting for reply...")

        try:
            await asyncio.wait_for(got_tts_stop.wait(), timeout=args.timeout)
            await asyncio.sleep(0.3)
        except asyncio.TimeoutError:
            print("! timed out waiting for tts stop", file=sys.stderr)
        read_task.cancel()

    if reply_pcm:
        with wave.open(args.out, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(reply_rate)
            out.writeframes(bytes(reply_pcm))
        print(f"\nwrote {args.out} ({len(reply_pcm) / 2 / reply_rate:.1f}s @ {reply_rate}Hz)")
        return 0

    print("\nno audio received", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (KeyboardInterrupt, websockets.ConnectionClosed):
        sys.exit(130)
