# VECTOR Voice Server

A drop-in replacement for the xiaozhi cloud backend. It speaks the
[xiaozhi-esp32 WebSocket protocol](https://github.com/78/xiaozhi-esp32/blob/main/docs/websocket.md),
so **stock firmware talks to it with one config change and no code edits**.

```
ESP32-S3  ──Opus 16k──▶  Opus decode ──▶ Deepgram (STT)
                                              │
                                              ▼
                                        Gemini (LLM)
                                              │  streamed by sentence
                                              ▼
ESP32-S3  ◀──Opus 24k──  Opus encode ◀──  TTS (edge / gemini / piper)
```

The ESP32 stays a thin client: mic capture, AEC/noise suppression, wake word,
Opus, display. All the intelligence is here.

---

## Why an OTA endpoint is required

The firmware has **no compile-time setting for the WebSocket URL**. The only
way it learns where to connect is:

1. It POSTs its system info to `CONFIG_OTA_URL`.
2. Whatever arrives in the response's `websocket` object is written to NVS
   (`main/ota.cc`).
3. `WebsocketProtocol::OpenAudioChannel()` reads the URL back from NVS.

So this server exposes both endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /xiaozhi/ota/` | Tells the device where the WebSocket lives |
| `WS /xiaozhi/v1/` | The conversation |
| `GET /health` | Liveness |

Three details in the OTA reply are load-bearing, and getting any of them wrong
is a silent failure:

- **Only a `websocket` block, never `mqtt`.** `Application::InitializeProtocol()`
  prefers MQTT whenever an `mqtt` object is present.
- **`firmware.version` but no `firmware.url`.** `Ota` only sets
  `has_new_version_` when *both* are strings, so omitting the URL guarantees the
  device never tries to flash itself from us. We echo back the version the
  device reported.
- **`timezone_offset` is in minutes**, not milliseconds — the firmware
  multiplies by `60 * 1000` itself. `330` = IST.

There is no `activation` block, so the device skips activation entirely.

---

## Run it on the laptop (Ubuntu 22)

```bash
sudo apt update && sudo apt install -y python3-venv libopus0 ffmpeg

cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

`libopus0` is loaded by `opuslib` through ctypes at import time, and `ffmpeg`
does MP3 decode plus resampling in the TTS path. Both are also in the Docker
image.

Edit `.env`:

```bash
DEEPGRAM_API_KEY=...
GEMINI_API_KEY=...
VECTOR_PUBLIC_HOST=192.168.1.50:8000   # your LAN IP, NOT localhost
```

`VECTOR_PUBLIC_HOST` is what gets handed to the ESP32. It must be reachable
*from the device*, so `127.0.0.1` will never work. Find it with:

```bash
hostname -I | awk '{print $1}'
```

### Pick a live Gemini model first

`gemini-2.5-flash` started returning 404 in July 2026, ahead of its announced
October shutdown. Don't trust any hardcoded default, including ours:

```bash
python tools/list_models.py
```

Set `GEMINI_MODEL` to something that actually came back. For a voice assistant
the turns are tiny (a few hundred tokens each), so the cheap tier is the right
call — `gemini-3.5-flash-lite` at $0.30/$2.50 per Mtok works out to roughly
₹0.08 per exchange, i.e. ~12,000 exchanges from ₹1000 of credit. Move up to
`gemini-3.6-flash` only when you start doing real planning.

### Start it

```bash
python -m vector_voice
```

---

## Test it without the ESP32

```bash
# terminal 2 -- pretend to be the device
python tools/fake_device.py --url ws://127.0.0.1:8000/xiaozhi/v1/ --wav question.wav
```

It performs the real handshake, streams 16 kHz Opus exactly like the firmware,
prints every message the server sends back, and writes the spoken reply to
`reply.wav`. Fastest way to iterate on prompts and voices.

Offline checks (no keys, no network, no hardware):

```bash
python tests/test_session.py
```

These cover the handshake contract, Opus round-tripping in both directions,
turn message ordering, and the playback pacing described below.

---

## Playback pacing

The firmware's decode queue is `MAX_DECODE_PACKETS_IN_QUEUE`
(`2400 / frame_duration` = **40 frames at 60 ms**) and it *silently drops the
overflow*. A 10-second reply is 167 frames, so sending as fast as TTS produces
would throw most of it away and you would hear chopped audio with no error
anywhere.

So playback runs at most `VECTOR_PLAYBACK_BURST_FRAMES` (default 15 ≈ 900 ms)
ahead of realtime, and **that budget is per turn, not per sentence** — a reply
made of ten short sentences must not reset it ten times. `tests/test_session.py`
simulates the device's bounded queue and asserts zero drops.

---

## Move it to the Raspberry Pi

Nothing is architecture-specific. `python:3.11-slim-bookworm` has official
arm64 images, and `libopus0`/`ffmpeg` are in Debian arm64.

```bash
rsync -av --exclude .venv --exclude __pycache__ server/ pi@raspberrypi:~/vector-server/
ssh pi@raspberrypi
cd ~/vector-server

# point the device at the Pi instead of the laptop
sed -i 's/^VECTOR_PUBLIC_HOST=.*/VECTOR_PUBLIC_HOST=192.168.1.60:8000/' .env

docker compose up -d --build
docker compose logs -f
```

`network_mode: host` keeps the audio path off the Docker NAT hop and makes the
LAN IP in `.env` the actual bind address. The image builds in ~2 min on a Pi 5.

The device caches the WebSocket URL in NVS, so after changing
`VECTOR_PUBLIC_HOST` let the ESP32 hit the OTA endpoint once (reboot it) before
expecting it to find the new host.

---

## Point the ESP32 at this server

Wiring, menuconfig settings and bring-up order are in
[`../firmware/README.md`](../firmware/README.md). The short version, in the
xiaozhi-esp32 checkout:

```bash
idf.py set-target esp32s3
idf.py menuconfig   # Xiaozhi Assistant -> Default OTA URL -> http://<LAN-IP>:8000/xiaozhi/ota/
idf.py build flash monitor
```

Plain `ws://` and `http://` are fine on a LAN and make development far easier —
no certificates to wrangle. Add TLS only when the server leaves your network.

---

## Swapping providers

| Knob | Options |
|---|---|
| `TTS_PROVIDER` | `edge` (free, no signup, no key) · `gemini` (uses your credits) · `piper` (fully local, offline) |
| `DEEPGRAM_MODEL` | `nova-3`, etc. |
| `DEEPGRAM_LANGUAGE` | `multi` handles Hindi/English code-switching; `en-IN` pins to English |
| `GEMINI_MODEL` | anything `tools/list_models.py` reports |

**On TTS:** `edge` is the recommended starting point — Microsoft's neural voices
at no cost and with no account, including `en-IN-NeerjaNeural`. It is an
unofficial endpoint, so treat it as best-effort: if it ever goes away, switch
`TTS_PROVIDER` and nothing else changes. `piper` is the insurance policy, since
it runs entirely on the Pi with no network at all.

List Edge voices with `edge-tts --list-voices`.

---

## Turn-taking

The firmware's default listening mode is `kListeningModeAutoStop`: the device
streams continuously and the **server** decides when the user stopped talking.
That decision is Deepgram's `endpointing` (default 400 ms of silence) plus
`UtteranceEnd` as a safety net.

- Getting cut off mid-sentence → raise `DEEPGRAM_ENDPOINTING_MS`
- Long pause before it replies → lower it

After `tts stop` the device returns to listening and sends its own
`listen start`, so the server never re-arms the microphone on its own — doing so
would open a stream in manual mode, where the device has gone idle instead.

---

## Not built yet

- **MCP bridge.** The firmware already exposes its capabilities as MCP tools
  over this same socket (`main/mcp_server.cc`). Mapping those onto Gemini
  function calling is the next milestone and the thing that turns this from a
  chatbot into VECTOR's actuator layer. Incoming `type: "mcp"` messages are
  currently logged so you can see the device's tool list while developing.
- **Long-term memory.** History is in-process and dies with the connection.
- **Multi-device.** Each connection gets its own `Session`; there is no shared
  state or per-device identity beyond the `Device-Id` header.
