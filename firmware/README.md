# VECTOR Firmware — ESP32-S3 + INMP441 + MAX98357

The firmware is stock [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32).
Nothing is forked or patched — the entire pipeline swap happens server-side, and
the device only needs to be told where to connect.

Your hardware maps exactly onto the project's `bread-compact-wifi` board, which
is **already the default for ESP32-S3**. It uses `NoAudioCodecSimplex`: two
independent I2S peripherals, one for the INMP441 and one for the MAX98357, which
is precisely the "raw I2S mic + raw I2S amp, no codec chip" topology you have.

---

## Wiring

Pins come from `main/boards/bread-compact-wifi/config.h`.

### INMP441 microphone (I2S port 1, RX)

| INMP441 | ESP32-S3 |
|---|---|
| VDD | 3V3 |
| GND | GND |
| SCK | **GPIO 5** |
| WS | **GPIO 4** |
| SD | **GPIO 6** |
| **L/R** | **GND** |

⚠️ **L/R must go to GND.** The RX slot mask is hardcoded to
`I2S_STD_SLOT_LEFT` (`main/audio/codecs/no_audio_codec.cc:110`), so the mic has
to be on the left channel. L/R tied to VDD puts it on the right slot and you get
a perfectly silent microphone with no error anywhere in the log. This is the
single most common bring-up failure with this combination.

### MAX98357 amplifier (I2S port 0, TX)

| MAX98357 | ESP32-S3 |
|---|---|
| VIN | 5V (or 3V3 — quieter) |
| GND | GND |
| BCLK | **GPIO 15** |
| LRC | **GPIO 16** |
| DIN | **GPIO 7** |

The TX slot mask is also `I2S_STD_SLOT_LEFT`. If output is audible but weak,
that's the `SD_MODE` pin: left floating, most breakouts run in (L+R)/2 mode,
which halves the level when only the left slot carries data. Tying `SD_MODE`
high forces left-channel mode. Check your specific breakout's datasheet — the
resistor networks differ between vendors.

### Optional, wired only if you have the parts

| Function | GPIO |
|---|---|
| Onboard LED | 48 |
| Boot button (push-to-talk) | 0 |
| Touch button | 47 |
| Volume up / down | 40 / 39 |
| OLED SDA / SCL | 41 / 42 |
| Lamp (the MCP demo tool) | 18 |

**No OLED is fine.** `esp_lcd_panel_init()` fails the I2C transaction, the board
logs `Failed to initialize display` and falls back to `NoDisplay()`. You still
have to *select* an OLED type in menuconfig though, or `config.h` hits
`#error "OLED display type is not selected"` at compile time. Leave the default.

None of these pins collide with octal PSRAM (which consumes GPIO 33–37) or with
native USB (GPIO 19/20).

---

## Check your board's PSRAM first

This is the one thing that can stop you dead. `sdkconfig.defaults.esp32s3` sets:

```
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_OCT=y
```

**Octal** PSRAM. That is the `R8` suffix — an `N16R8` devkit is what you want and
what most two-USB-C S3 boards are. But:

| Your board | What to do |
|---|---|
| **N16R8** (16 MB flash, 8 MB octal PSRAM) | Nothing. Defaults are correct. |
| **N8R8** (8 MB flash, 8 MB octal) | Set flash size to 8 MB + `partitions/v2/8m.csv` (below) |
| **N8R2 / N16R2** (quad PSRAM) | Change to `CONFIG_SPIRAM_MODE_QUAD=y` |
| **No PSRAM** | AFE wake word is impossible — set `WAKE_WORD_DISABLED` and use the boot button |

Wake word needs PSRAM: `USE_AFE_WAKE_WORD` is gated on
`(IDF_TARGET_ESP32S3 || ...) && SPIRAM` in `main/Kconfig.projbuild`.

Read the boot log to find out what you actually have — it prints the SPI RAM
mode and size explicitly:

```bash
idf.py -p /dev/ttyACM0 monitor
```

If flash is 8 MB rather than 16 MB, add to `sdkconfig.defaults` (or set in
menuconfig):

```
CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions/v2/8m.csv"
```

---

## Build

```bash
git clone https://github.com/78/xiaozhi-esp32.git
cd xiaozhi-esp32
idf.py set-target esp32s3
idf.py menuconfig
```

Four settings under **`Xiaozhi Assistant`**:

| Setting | Value |
|---|---|
| Board Type | `Bread Compact WiFi` (already the S3 default) |
| Default OTA URL | `http://192.168.1.50:8000/xiaozhi/ota/` ← your laptop's LAN IP |
| Default Language | English (ships as Chinese) |
| Wake Word Implementation Type | `Wakenet model with AFE` |

Then the wake word model itself, under **`ESP Speech Recognition`**. The default
is `CONFIG_SR_WN_WN9_NIHAOXIAOZHI_TTS` — Chinese, "ni hao xiao zhi". Switch to an
English model (`hiesp` / `alexa` are the ones shipped in the open esp-sr
package). Saying "vector" needs either a custom-trained WakeNet model from
Espressif, or the `USE_CUSTOM_WAKE_WORD` MultiNet path with an English phoneme
string — plan on tuning `CUSTOM_WAKE_WORD_THRESHOLD` if you go that route.

```bash
idf.py build flash monitor
```

**Flash over the UART port**, not the USB-OTG one. Your board has two USB-C
ports: one is the native USB peripheral (GPIO 19/20), the other goes through the
UART bridge and is labelled `COM` or `UART`. The UART port just works; the
native port needs BOOT held down while connecting.

---

## The sample rates already line up

```c
#define AUDIO_INPUT_SAMPLE_RATE  16000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000
```

The server uploads at 16 kHz and the server's default downlink is 24 kHz, so
`AudioService` skips both its input and output resamplers entirely. That is the
best case for a device this small — don't change
`VECTOR_DOWNLINK_SAMPLE_RATE` away from 24000 without a reason.

---

## Bring-up order

Work outward from the thing you can see, so a failure only ever has one possible
cause:

1. **Serial boots clean.** No PSRAM panic, no I2S error. Confirms the board.
2. **`ota check` appears in the server log** when the device boots. Confirms
   WiFi, the OTA URL, and that the device accepted your config JSON. If the
   device never appears, it cannot reach your laptop — check the LAN IP and
   your firewall (`sudo ufw allow 8000`).
3. **`device connected` in the server log.** Confirms the WebSocket URL made it
   into NVS and the handshake succeeded.
4. **Say something, watch for `user: ...`** in the server log. Confirms the mic,
   the I2S left-slot wiring, Opus encode, and Deepgram.
5. **Hear the reply.** Confirms TTS, Opus decode, and the amp.

Step 4 failing while 1–3 pass is almost always the INMP441 L/R pin.

---

## Changing the server address later

The WebSocket URL is cached in NVS. After you move the server from the laptop to
the Pi and update `VECTOR_PUBLIC_HOST`, the device has to hit the OTA endpoint
once more to pick up the change — so reboot it. If you also changed the OTA URL
itself, reflash. A full NVS erase (`idf.py erase-flash`) resets everything
including the `Client-Id` UUID.
