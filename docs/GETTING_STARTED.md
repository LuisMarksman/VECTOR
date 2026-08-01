# VECTOR Voice — Getting Started

End-to-end bring-up for: Ubuntu 22 laptop → ESP32-S3 → Raspberry Pi.

**Hardware assumed:** ESP32-S3 **N16R8** (two USB-C ports), INMP441 mic,
MAX98357 amp, 0.96" SSD1306 OLED.

Each phase ends in a checkpoint. Don't move on until it passes — a failure at a
checkpoint has one cause, a failure three phases later has ten.

---

## Phase 1 — Wire the hardware

Power off while wiring.

**INMP441 microphone**

| INMP441 | ESP32-S3 |
|---|---|
| VDD | 3V3 |
| GND | GND |
| SCK | GPIO 5 |
| WS | GPIO 4 |
| SD | GPIO 6 |
| **L/R** | **GND** |

**L/R to GND is not optional.** The firmware's RX slot mask is hardcoded to
`I2S_STD_SLOT_LEFT`. L/R left floating or tied high gives you a silent
microphone and a completely clean log — nothing to debug.

**MAX98357 amplifier**

| MAX98357 | ESP32-S3 |
|---|---|
| VIN | 5V |
| GND | GND |
| BCLK | GPIO 15 |
| LRC | GPIO 16 |
| DIN | GPIO 7 |

Speaker goes to the `+` / `-` screw terminals. 4Ω or 8Ω, 3W or less.

**SSD1306 OLED**

| OLED | ESP32-S3 |
|---|---|
| GND | GND |
| VCC | 3V3 |
| SCL | GPIO 42 |
| SDA | GPIO 41 |

**Checkpoint:** Both GND rails common, nothing on GPIO 19/20 (native USB) or
GPIO 33–37 (octal PSRAM).

---

## Phase 2 — Run the server on the laptop

Do this *before* touching the ESP32. You can prove the entire AI pipeline works
with no hardware at all, which means any later failure is hardware.

```bash
sudo apt update
sudo apt install -y python3-venv libopus0 ffmpeg git

git clone https://github.com/LuisMarksman/VECTOR.git
cd VECTOR/server
git checkout claude/xiaozhi-esp32-pipeline-qiarh0

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`libopus0` is loaded by `opuslib` through ctypes at import; `ffmpeg` does MP3
decode and resampling. Missing either gives an import-time or first-reply crash.

### 2.1 Find your LAN IP

```bash
hostname -I | awk '{print $1}'      # e.g. 192.168.1.50
```

This is what the ESP32 will dial. `127.0.0.1` will never work — the device is a
different machine.

### 2.2 Configure

```bash
cp .env.example .env
nano .env
```

Set four values:

```bash
DEEPGRAM_API_KEY=<your deepgram key>
GEMINI_API_KEY=<your gemini key>
VECTOR_PUBLIC_HOST=192.168.1.50:8000     # YOUR ip from 2.1
GEMINI_MODEL=gemini-3.5-flash-lite
```

Leave `TTS_PROVIDER=edge`.

### 2.3 Verify the three services independently

Each of these fails loudly and separately, which is the point.

```bash
# Gemini — should print a list of models
python tools/list_models.py

# edge-tts — should produce an audible mp3
edge-tts --voice en-IN-NeerjaNeural --text "VECTOR online" --write-media /tmp/t.mp3
ffplay -autoexit -nodisp /tmp/t.mp3

# Deepgram — should print 200
curl -s -o /dev/null -w "%{http_code}\n" https://api.deepgram.com/v1/projects \
  -H "Authorization: Token $(grep DEEPGRAM_API_KEY .env | cut -d= -f2)"
```

A `401` from Deepgram means a bad key. A `403`/timeout from edge-tts means the
endpoint is blocked or gone — switch `TTS_PROVIDER=piper` and carry on.

### 2.4 Start it

```bash
python -m vector_voice
```

Expect: `listening on 0.0.0.0:8000 | stt=deepgram/nova-3 llm=... tts=edge`

### 2.5 Test the whole pipeline with no ESP32

Record a question, then feed it in as if you were the device:

```bash
# terminal 2
cd VECTOR/server && source .venv/bin/activate

# record 4 seconds -- say "what is the capital of India?"
ffmpeg -f alsa -i default -t 4 -ar 16000 -ac 1 /tmp/question.wav

python tools/fake_device.py --url ws://127.0.0.1:8000/xiaozhi/v1/ --wav /tmp/question.wav
ffplay -autoexit -nodisp reply.wav
```

**Checkpoint:** you see `stt`, `speak`, `tts stop` in the output and hear a
spoken answer in `reply.wav`. Everything except the ESP32 now works.

### 2.6 Open the firewall

```bash
sudo ufw allow 8000/tcp     # only if ufw is active
```

---

## Phase 3 — Build and flash the firmware

### 3.1 Install ESP-IDF (once, ~20 min)

```bash
sudo apt install -y git wget flex bison gperf python3-pip python3-venv \
     cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0

mkdir -p ~/esp && cd ~/esp
git clone -b v5.5.5 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32s3
```

The project requires IDF ≥ 5.5.2; v5.5.5 is the current 5.5.x.

Every new terminal that builds firmware needs:

```bash
. ~/esp/esp-idf/export.sh
```

### 3.2 Serial permissions (once)

```bash
sudo usermod -aG dialout $USER
```

**Log out and back in**, or the group won't apply.

### 3.3 Get the firmware

```bash
cd ~ && git clone https://github.com/78/xiaozhi-esp32.git
cd xiaozhi-esp32
idf.py set-target esp32s3
```

### 3.4 Configure

```bash
idf.py menuconfig
```

Under **`Xiaozhi Assistant`**:

| Setting | Value |
|---|---|
| Board Type | `Bread Compact WiFi` — already the S3 default |
| Default OTA URL | `http://192.168.1.50:8000/xiaozhi/ota/` ← **your** IP |
| Default Language | `English` |
| OLED Type | **`SSD1306 128*64`** ← default is 128×32, wrong for a 0.96" panel |
| Wake Word Implementation Type | `Wakenet model with AFE` |

Under **`ESP Speech Recognition`**: change the wake word model from the Chinese
default (`nihaoxiaozhi`) to an English one — `hiesp` or `alexa`.

Note the trailing slash on the OTA URL. Save and exit.

Nothing else needs changing: N16R8 means the octal-PSRAM and 16 MB flash
defaults are already correct for your board.

### 3.5 Flash

Plug into the **UART port** (the one via the USB-serial bridge, usually labelled
`COM`/`UART`). It appears as `/dev/ttyUSB0`. The other port is native USB
(`/dev/ttyACM0`) and needs BOOT held down while connecting.

```bash
ls /dev/ttyUSB* /dev/ttyACM*        # confirm which appeared
idf.py -p /dev/ttyUSB0 build flash monitor
```

First build takes ~10 minutes. `Ctrl+]` exits the monitor.

### 3.6 Join WiFi

On first boot the device starts its own hotspot. Connect a phone to the
`Xiaozhi-XXXX` network, open the captive portal, and give it your WiFi
credentials. **The ESP32 must be on the same network as the laptop** — and note
the ESP32 is 2.4 GHz only, so if your router splits SSIDs, pick the 2.4 GHz one.

**Checkpoint:** the serial monitor shows an IP address and no PSRAM or I2S
errors.

---

## Phase 4 — First conversation

Watch the server terminal. In order, you should see:

1. `ota check: device=... version=... -> ws://192.168.1.50:8000/xiaozhi/v1/`
2. `device connected: aa:bb:cc:...`
3. Say the wake word, then ask something → `user: what is the capital of india`
4. `first sentence in 1.1s` → `vector: ...` → you hear it

**Checkpoint:** you had a conversation.

### If it stalls

| Symptom | Cause |
|---|---|
| No `ota check` at all | Device can't reach the laptop. Wrong IP, wrong network, or firewall. |
| `ota check` but no `device connected` | Wrong `VECTOR_PUBLIC_HOST` — it's baked into the OTA reply. Fix `.env`, restart server, reboot device. |
| Connects, but no `user:` line ever | **The INMP441 L/R pin.** Almost always. |
| `user:` appears but no audio comes back | TTS. Re-run the 2.3 edge-tts check. |
| Audio is choppy | WiFi. Move closer to the router. |
| Half the OLED is dead | You left OLED Type at 128×32. |

---

## Phase 5 — Move the server to the Raspberry Pi

Only after Phase 4 works.

```bash
# from the laptop
rsync -av --exclude .venv --exclude __pycache__ VECTOR/server/ pi@raspberrypi:~/vector-server/

ssh pi@raspberrypi
cd ~/vector-server
hostname -I | awk '{print $1}'        # the Pi's IP, e.g. 192.168.1.60

sed -i 's/^VECTOR_PUBLIC_HOST=.*/VECTOR_PUBLIC_HOST=192.168.1.60:8000/' .env
docker compose up -d --build
docker compose logs -f
```

The image is `python:3.11-slim-bookworm`, which has official arm64 builds;
nothing in the stack is architecture-specific. Build takes ~2 min on a Pi 5.

Then repoint the device — the OTA URL is compiled in, so this needs a reflash:

```bash
# on the laptop, in xiaozhi-esp32
idf.py menuconfig      # Default OTA URL -> http://192.168.1.60:8000/xiaozhi/ota/
idf.py -p /dev/ttyUSB0 build flash
```

Give the Pi a DHCP reservation in your router, or its IP will move and you'll be
reflashing again.

**Checkpoint:** laptop off, conversation still works.

---

## What to do next

- Change `VECTOR_SYSTEM_PROMPT` in `.env` — biggest quality lever, costs nothing
- Try other voices: `edge-tts --list-voices | grep en-IN`
- Tune `DEEPGRAM_ENDPOINTING_MS` — lower if it's slow to reply, higher if it
  cuts you off mid-sentence
- Then the MCP bridge, which is what turns this from a chatbot into something
  that can actually control hardware
