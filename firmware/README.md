# VECTOR Firmware

Embedded nodes that connect physical devices to VECTOR over WiFi + MQTT. They
speak the same topic contract as the server, so they appear as devices the
assistant can see and control with no extra glue.

| Project       | Board                 | Role |
|---------------|-----------------------|------|
| `esp32_node`  | ESP32 (esp32dev)      | Smart-home actuator: relay/light + button, `home/<id>/set` ⇄ `state` |
| `xiao_sense`  | Seeed XIAO ESP32S3    | Wireless sensor: motion + heartbeat → `home/<id>/state` |

Both are built with [PlatformIO](https://platformio.org/) using the Arduino
framework and the `PubSubClient` (MQTT) + `ArduinoJson` libraries.

## Build & flash

```bash
# Install PlatformIO Core:  pip install platformio
cd firmware/esp32_node          # or firmware/xiao_sense

cp include/config.example.h include/config.h   # then edit WiFi / MQTT / pins
pio run -t upload               # compile + flash over USB
pio device monitor              # watch the serial log
```

> `config.h` holds your WiFi/MQTT credentials and is git-ignored — never commit
> it. Only `config.example.h` is tracked.

## How it fits together

```
ESP32 / XIAO  ──MQTT──►  broker  ◄──►  VECTOR server (HomeAutomation)
   set/state topics       :1883        vector/home/<id>/set | /state
```

Try it end to end once flashed and the server is running:

```bash
# Turn the ESP32's relay on through the server's API:
curl -X POST http://<server>:8000/home/devices/living-room-lamp/command \
  -H 'content-type: application/json' -d '{"action": "on"}'

# ...or just ask the assistant:
curl -X POST http://<server>:8000/assistant/command \
  -H 'content-type: application/json' -d '{"text": "turn on the living room lamp"}'
```

## Notes

- The device `DEVICE_ID` in `config.h` becomes the device id the server sees,
  e.g. `living-room-lamp` → topics `vector/home/living-room-lamp/{set,state}`.
- State is published **retained** with a last-will message, so the server always
  has a current view of each device — even across reconnects.
- The XIAO Sense has an on-board camera; `xiao_sense/src/main.cpp` documents how
  to extend it into a streaming source for the `vision` worker.
