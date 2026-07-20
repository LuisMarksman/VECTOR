# ESP32 GPS → Telegram Bot

Sends the GPS location from a **NEO-6M (GY-GPS6MV2)** module to a **Telegram bot**
using an **ESP32 DevKit v1**.

## Hardware wiring

| GPS (NEO-6M) | ESP32 DevKit v1 |
|--------------|-----------------|
| VCC          | 3.3V            |
| GND          | GND             |
| TX           | GPIO16 (RX2)    |
| RX           | GPIO17 (TX2)    |

> Note: GPS **TX** goes to ESP32 **RX**, and GPS **RX** goes to ESP32 **TX** (crossed).

## Arduino IDE setup

1. **Board support:** In *Tools → Board → Boards Manager*, install
   **"esp32" by Espressif Systems**. Then select **DOIT ESP32 DEVKIT V1**.
2. **Libraries** (*Tools → Manage Libraries*):
   - `TinyGPSPlus` by Mikal Hart
   - `UniversalTelegramBot` by Brian Lough
   - `ArduinoJson` (v6.x)

## Telegram setup

1. Message **@BotFather** on Telegram → `/newbot` → copy the **bot token**.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` in a browser and
   read the `"chat":{"id": ...}` value — that's your **CHAT_ID**.

## Configure the sketch

Edit these values at the top of `esp32_gps_telegram.ino`:

```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
#define BOT_TOKEN "YOUR_TELEGRAM_BOT_TOKEN"
#define CHAT_ID  "YOUR_CHAT_ID"
```

## Usage

- The device sends its location automatically every 60 seconds
  (change `SEND_INTERVAL_MS`, set to `0` to disable).
- Send **`/location`** to the bot at any time to get the current position.
- Location messages include a clickable Google Maps link.

The NEO-6M needs a clear view of the sky and may take 30 s–a few minutes for a
first fix (the on-board LED blinks once locked).
