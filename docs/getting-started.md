# Getting Started

This guide gets the VECTOR "brain" running on your machine and shows how to talk
to it — no hardware, API keys or robot required.

## Prerequisites

- **Python 3.11+**
- **Docker** (optional, for the one-command stack)
- **Git**

## 1. Clone & configure

```bash
git clone https://github.com/LuisMarksman/VECTOR.git
cd VECTOR
make env          # creates .env from .env.example
```

The defaults are offline-friendly: `VECTOR_LLM_PROVIDER=mock` and a
fault-tolerant bus mean nothing external is required.

## 2. Run the server

### Option A — Docker (server + MQTT broker)

```bash
make up           # docker compose up -d mqtt server
curl http://localhost:8000/health
```

### Option B — Local Python

```bash
cd server
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open the interactive API docs at <http://localhost:8000/docs>.

## 3. Talk to VECTOR

```bash
curl -X POST http://localhost:8000/assistant/command \
  -H 'content-type: application/json' \
  -d '{"text": "turn on the living room lights and vacuum the floor"}'
```

You'll get back a plan with one step per clause, each routed to a capability and
executed. That's the reason → plan → act loop in action.

## 4. Add the voice front-end

```bash
cd voice
pip install -r requirements.txt
python -m vector_voice          # console mode: type instead of speaking
```

## 5. Add the vision worker

```bash
cd vision
pip install -r requirements.txt
python -m vector_vision          # mock camera publishes detections
curl http://localhost:8000/vision/events
```

## 6. Go further

- **Real reasoning** — set `VECTOR_LLM_PROVIDER=anthropic` (or `openai`) and the
  matching API key in `.env`, then `pip install -e "server[anthropic]"`.
- **Real devices** — flash a board from [`../firmware`](../firmware) and point it
  at your broker; it appears as a controllable device automatically.
- **The robot** — build the ROS2 workspace in [`../robotics`](../robotics) and
  launch `vector_bringup`.

## Handy commands

```bash
make test         # run the server test suite
make lint         # ruff checks
make server       # run the API with autoreload
make up / down    # start / stop the Docker stack
make logs         # tail server logs
```

## Troubleshooting

- **`/health` shows `mqtt_connected: false`** — expected without a broker; the
  server runs degraded. Start one with `docker compose up mqtt`.
- **LLM replies look canned** — you're on the `mock` provider. Configure a real
  one (step 6).
- **Port 8000 in use** — set `VECTOR_SERVER_PORT` in `.env`.
