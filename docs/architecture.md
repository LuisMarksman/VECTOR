# VECTOR Architecture

VECTOR is a **monorepo of cooperating components** that together turn natural
language into physical and digital action. This document explains how the pieces
fit and how a single request flows through the system.

## Components

```
                    ┌───────────────────────────────────────────┐
      Voice / Web / │                 VECTOR Server              │
      Mobile  ─────►│  API ─► Agent ─► Planner ─► Executors      │
                    │           │        │                        │
                    │        Memory     LLM                       │
                    └───────────────┬───────────────────────────┘
                                    │ MQTT message bus
        ┌───────────────┬──────────┴───────────┬──────────────────┐
        ▼               ▼                      ▼                  ▼
   Smart home      Mobile robot            Robot arm           Vision
   (firmware)      (ROS2 + bridge)         (ROS2)            (worker/eye)
```

| Component | Tech | Role |
|-----------|------|------|
| **server** | Python, FastAPI | The brain: reason, plan, orchestrate |
| **voice** | Python | Wake word → STT → server → TTS |
| **vision** | Python, OpenCV/YOLO | Detection, faces, tracking, OCR |
| **robotics** | ROS2 | Mobile base, arm, perception, MQTT bridge |
| **firmware** | C++, ESP32 | Smart-home actuators & sensors |
| **integrations** | MQTT/Home Assistant | The bus + third-party bridges |

## The server, in layers

The server is deliberately layered so the core logic is testable without HTTP or
hardware:

1. **API** (`app/api`) — thin FastAPI adapters.
2. **Agent** (`app/core/agent.py`) — the reason → plan → act loop.
3. **Planner** (`app/core/planner.py`) — decomposes a command into steps and
   routes each to a capability.
4. **Executors** — `home_automation.py`, `robot_manager.py` publish to the bus;
   `llm.py` handles conversation.
5. **Memory** (`app/core/memory.py`) — history + long-term facts.
6. **Bus** (`app/core/bus.py`) — fault-tolerant MQTT wrapper.

See [`../server/README.md`](../server/README.md) for the module map.

## Request lifecycle

Consider:

> "Turn on the living room lights, then bring me my water bottle."

1. **Capture** — the voice client transcribes speech and POSTs
   `{"text": "…"}` to `/assistant/command` (or the web/mobile UI does).
2. **Plan** — the planner splits the request on *"then"* into two steps and
   classifies them: `home_automation` and `robot`.
3. **Act** —
   - Step 1 → `HomeAutomation.command("living-room-lights", on)` →
     publishes `vector/home/living-room-lights/set`. The ESP32 node switches the
     relay and reports `…/state`.
   - Step 2 → `RobotManager.dispatch("mobile-1", deliver)` →
     publishes `vector/robot/mobile-1/cmd`. The ROS2 bridge turns it into a
     `/cmd_vel` / navigation goal; the arm later performs the pick.
4. **Respond** — the agent composes a reply ("Here's what I did: …"), stores it
   in memory, and returns it; the voice client speaks it.

The design means each component can be developed and tested independently: the
server runs with mock LLM + a disabled bus, the voice and vision workers run with
console/mock backends, and the robot nodes run in simulation.

## Message bus contract

Everything physical is reached through MQTT using the topic contract in
[`mqtt-topics.md`](mqtt-topics.md). This decouples the "brain" from the "body":
the server never imports ROS2 or talks to a GPIO pin — it publishes intent, and
the robots/firmware realise it.

## Design principles

- **Runs out of the box.** Mock/console/disabled fallbacks everywhere, so the
  whole stack starts with no API keys, no broker and no hardware.
- **Config over hard-coding.** All wiring comes from environment variables.
- **Thin edges, testable core.** HTTP/ROS2/firmware are adapters around
  dependency-light core logic.
- **One contract.** The MQTT topic tree + the server's Pydantic schemas are the
  single interface between components.
