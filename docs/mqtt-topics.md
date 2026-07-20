# MQTT Topic Contract

MQTT is VECTOR's nervous system. Every component — server, robots, vision,
voice and firmware — communicates through a shared, namespaced topic tree. This
document is the source of truth for that contract.

All topics are prefixed with a configurable base (`VECTOR_MQTT_BASE_TOPIC`,
default `vector`). Payloads are JSON.

## Conventions

- `…/set` / `…/cmd` — **commands** (server → device/robot)
- `…/state` — **state reports** (device/robot → server), usually **retained**
- `<id>` — a device or robot identifier (e.g. `living-room-lamp`, `mobile-1`)

## Topics

### Smart home
| Topic | Direction | Payload |
|-------|-----------|---------|
| `vector/home/<id>/set` | server → device | `{"action": "on" \| "off" \| "set", "value": <any>}` |
| `vector/home/<id>/state` | device → server | `{"device_id","kind","online","state":{…}}` |

### Mobile robot
| Topic | Direction | Payload |
|-------|-----------|---------|
| `vector/robot/<id>/cmd` | server → robot | `{"action": "navigate" \| "clean" \| "deliver" \| "dock" \| "stop", "params": {…}}` |
| `vector/robot/<id>/state` | robot → server | `{"online","battery","pose":{…},"status"}` |

### Robot arm
| Topic | Direction | Payload |
|-------|-----------|---------|
| `vector/arm/cmd` | server → arm | `{"action": "pick" \| "place" \| "home", "target": {…}}` |
| `vector/arm/state` | arm → server | `{"online","status","joints":[…]}` |

### Vision
| Topic | Direction | Payload |
|-------|-----------|---------|
| `vector/vision/detections` | vision → server | `{"source","detections":[{"label","confidence","box":{…}}]}` |

### Voice
| Topic | Direction | Payload |
|-------|-----------|---------|
| `vector/voice/command` | voice → server | `{"text","session_id"}` |
| `vector/assistant/reply` | server → voice | `{"text","session_id"}` |

> The voice client and vision worker in this repo currently use the server's
> **HTTP** API (`/assistant/command`, `/vision/events`); the MQTT topics above
> are the equivalent bus-native channels for fully decoupled deployments.

## Who publishes / subscribes

| Component | Publishes | Subscribes |
|-----------|-----------|------------|
| Server (`RobotManager`) | `robot/<id>/cmd`, `arm/cmd` | `robot/+/state` |
| Server (`HomeAutomation`) | `home/<id>/set` | `home/+/state` |
| `vector_bridge` (ROS2) | `robot/<id>/state` | `robot/<id>/cmd`, `arm/cmd` |
| ESP32 / XIAO firmware | `home/<id>/state` | `home/<id>/set` |
| Vision worker | `vision/detections` | — |

## Inspecting the bus

```bash
# Watch everything:
mosquitto_sub -h localhost -t 'vector/#' -v

# Manually command a device:
mosquitto_pub -h localhost -t 'vector/home/living-room-lamp/set' -m '{"action":"on"}'
```

## Design rules

1. **State is retained.** Devices publish state with the retain flag so the
   server has a current view immediately on connect.
2. **Commands are not retained.** They are events, not state.
3. **Use a last-will** so a device that drops off is marked `online: false`.
4. **Keep payloads small and flat.** They map directly to the server's
   Pydantic schemas in `server/app/models/schemas.py`.
