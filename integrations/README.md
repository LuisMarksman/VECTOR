# VECTOR Integrations

The integration layer connects VECTOR to the outside world: the MQTT message
bus that binds every component together, and bridges to third-party smart-home
ecosystems.

## Contents

| Path                     | What it is |
|--------------------------|------------|
| `mqtt/mosquitto.conf`    | Broker config used by `docker-compose` |
| `home_assistant/`        | Optional bridge to [Home Assistant](https://www.home-assistant.io/) |

## The message bus

MQTT is VECTOR's nervous system. Every subsystem — server, robots, vision,
voice, firmware — communicates through it using a shared topic contract defined
in [`../docs/mqtt-topics.md`](../docs/mqtt-topics.md).

Start a broker locally with Docker:

```bash
docker compose up mqtt          # from the repo root
```

Then watch everything flowing across the bus:

```bash
mosquitto_sub -h localhost -t 'vector/#' -v
```

## Smart-home bridges

VECTOR's home-automation contract (`vector/home/<id>/set` and `.../state`)
mirrors common smart-home conventions, so bridging is mostly configuration:

- **Home Assistant** — point HA's MQTT integration at the same broker and use
  MQTT Discovery, or run the example bridge in `home_assistant/` to mirror
  entities in both directions. See `home_assistant/README.md`.
- **Tasmota / ESPHome devices** — re-map their topics onto `vector/home/...`
  with a broker-side topic remap, or flash the firmware in `../firmware/`.
