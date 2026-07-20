# Home Assistant bridge

VECTOR and [Home Assistant](https://www.home-assistant.io/) can share the same
MQTT broker. This folder shows how to surface VECTOR devices in Home Assistant
automatically using [MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery).

## How it works

Home Assistant listens on `homeassistant/#` for *discovery* messages that
describe an entity and which topics to use. `discovery.py` publishes a discovery
config that maps a VECTOR device (`vector/home/<id>/{set,state}`) to a Home
Assistant `light`, so it appears in the HA UI and can be controlled from either
side.

## Usage

```bash
pip install paho-mqtt
python discovery.py --device living-room-lamp --name "Living Room Lamp" \
    --mqtt-host localhost
```

Prerequisites:

- The MQTT broker is running (`docker compose up mqtt`).
- Home Assistant's MQTT integration points at the same broker with discovery
  enabled (the default `homeassistant` prefix).
