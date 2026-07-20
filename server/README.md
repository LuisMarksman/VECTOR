# VECTOR Server

The **brain** of VECTOR. A FastAPI service that turns natural-language commands
into plans and executes them across the smart home, robots and vision workers.

```
        HTTP / voice / web
                │
          ┌─────▼──────┐
          │   Agent    │  reason → plan → act
          ├────────────┤
          │  Planner   │  decompose a command into steps
          │  Memory    │  conversation history + facts
          │  LLM       │  mock | anthropic | openai
          └─────┬──────┘
                │  MQTT message bus
   ┌────────────┼───────────────┐
   ▼            ▼               ▼
 Home Auto   RobotManager    Vision events
```

## Architecture

| Layer            | Module                     | Responsibility |
|------------------|----------------------------|----------------|
| HTTP API         | `app/api/routes/`          | Thin adapters over the core services |
| Orchestration    | `app/core/agent.py`        | Reason → plan → act loop |
| Planning         | `app/core/planner.py`      | Command → ordered steps (keyword routing) |
| Reasoning        | `app/core/llm.py`          | Pluggable LLM backends |
| Memory           | `app/core/memory.py`       | History + long-term facts |
| Robots           | `app/core/robot_manager.py`| Dispatch to base & arm, track state |
| Smart home       | `app/core/home_automation.py` | Device control + state |
| Message bus      | `app/core/bus.py`          | Fault-tolerant MQTT wrapper |
| Wiring           | `app/services.py`          | Builds & wires the singletons |

The core layer has **no FastAPI imports**, so it is reusable from tests, a CLI
or background workers.

## Quick start

```bash
pip install -e ".[dev]"          # from the server/ directory
uvicorn app.main:app --reload    # http://localhost:8000  (docs at /docs)
pytest -q                        # run the tests
```

The default `VECTOR_LLM_PROVIDER=mock` and the fault-tolerant bus mean the
server runs with **no API keys and no MQTT broker**. Point it at real services
by editing the root `.env`.

## Key endpoints

| Method | Path                              | Description |
|--------|-----------------------------------|-------------|
| GET    | `/health`                         | Liveness + bus status |
| POST   | `/assistant/command`              | Plan & execute a command |
| GET    | `/assistant/history/{session}`    | Conversation transcript |
| GET    | `/robots`                         | Robot fleet state |
| POST   | `/robots/{id}/command`            | Send a robot command |
| POST   | `/robots/arm/command`             | Send an arm command |
| GET    | `/home/devices`                   | Smart-home device state |
| POST   | `/home/devices/{id}/command`      | Control a device |
| POST   | `/vision/events`                  | Ingest a detection event |

Example:

```bash
curl -X POST http://localhost:8000/assistant/command \
  -H 'content-type: application/json' \
  -d '{"text": "turn on the living room lights and vacuum the floor"}'
```

## Configuration

All settings come from environment variables prefixed with `VECTOR_`
(see the repository-root `.env.example`). Notable ones:

- `VECTOR_LLM_PROVIDER` — `mock` (default) · `anthropic` · `openai`
- `VECTOR_MQTT_HOST` / `VECTOR_MQTT_PORT` — message bus
- `VECTOR_MEMORY_BACKEND` — `sqlite` (default) · `postgres`
