# Contributing to VECTOR

Thanks for your interest in VECTOR — *Virtual Engine for Control, Tasks &
Operational Robotics*. This is an ambitious, multi-domain project (AI, vision,
robotics, embedded, smart home) and contributions of every size are welcome.

## Repository layout

VECTOR is a **monorepo**. Each top-level directory is an independent component
that talks to the others over the MQTT message bus and the server's HTTP API:

| Directory       | What lives here |
|-----------------|-----------------|
| `server/`       | The "brain": FastAPI AI server, agent, planner, memory, orchestration |
| `voice/`        | Voice assistant (wake word → STT → server → TTS) |
| `vision/`       | Computer vision workers (detection, faces, tracking, OCR) |
| `robotics/`     | ROS2 packages for the mobile base, arm and robot "eye" |
| `firmware/`     | ESP32 / XIAO embedded firmware (PlatformIO) |
| `integrations/` | Smart-home + MQTT contract and device bridges |
| `hardware/`     | Bill of materials, wiring and mechanical notes |
| `docs/`         | Architecture and how-to documentation |
| `assets/`       | Logos, diagrams and other static media |

Start with [`docs/architecture.md`](docs/architecture.md) to see how the pieces
fit together, and [`docs/mqtt-topics.md`](docs/mqtt-topics.md) for the message
contract that binds them.

## Getting started

```bash
git clone https://github.com/LuisMarksman/VECTOR.git
cd VECTOR
make env        # create .env from the template
make setup      # install Python deps for server / voice / vision
make test       # run the server test suite
make server     # start the API on http://localhost:8000
```

Prefer containers? `make up` starts the MQTT broker and the server with Docker.

## Development workflow

1. **Branch** from `main`: `git checkout -b feat/<short-description>`.
2. **Keep changes scoped** to one component where possible.
3. **Add tests** for new server behaviour (`server/tests/`).
4. **Format & lint** before committing: `make fmt && make lint`.
5. **Write a clear commit message** — imperative mood, explain the *why*.
6. **Open a pull request** and describe what changed and how you verified it.

## Coding conventions

- **Python** — 3.11+, type hints everywhere, formatted and linted with
  [ruff](https://docs.astral.sh/ruff/). Keep modules small and single-purpose.
- **C/C++ firmware** — PlatformIO project layout; keep pin maps in one header.
- **ROS2** — `ament_python` packages, one node per responsibility.
- **Config over hard-coding** — read settings from environment variables
  (see `.env.example`) rather than baking them in.

## Reporting issues

Please include: what you expected, what happened, the component involved, and
steps to reproduce. Hardware issues should include the board and wiring.

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
