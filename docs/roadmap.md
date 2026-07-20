# Roadmap

VECTOR is under active development. This roadmap tracks the journey from a
runnable skeleton to a complete personal-robotics ecosystem. It expands on the
phases in the top-level [README](../README.md).

## ✅ Phase 0 — Foundation (this scaffold)

- [x] Monorepo structure across all components
- [x] Runnable FastAPI server: agent, planner, memory, executors
- [x] MQTT message-bus contract + broker config
- [x] Voice pipeline (console-mode)
- [x] Vision worker (mock-mode) publishing detections
- [x] ROS2 packages: base, arm, perception, bridge
- [x] ESP32 / XIAO firmware talking to the bus
- [x] Docs, CI, tests

## Phase 1 — AI Voice Assistant, Vision, Home Automation

- [ ] Real wake-word + STT + TTS backends wired end to end
- [ ] YOLO object detection + face recognition in the vision worker
- [ ] Reminders, calendar and search capabilities in the agent
- [ ] Home Assistant two-way bridge

## Phase 2 — AI Server, Memory, Agentic Planner

- [ ] LLM-driven structured planner (beyond keyword routing)
- [ ] Persistent memory (SQLite/Postgres + vector store for recall)
- [ ] Tool/function calling for external services
- [ ] Multi-agent coordination

## Phase 3 — Autonomous Mobile Robot

- [ ] Nav2 navigation + SLAM mapping
- [ ] Real odometry from wheel encoders
- [ ] Docking & charging
- [ ] Vacuum-cleaning behaviour

## Phase 4 — Robot Arm

- [ ] MoveIt 2 motion planning
- [ ] Vision-guided pick-and-place
- [ ] Object delivery hand-off from base to arm

## Phase 5 — Complete Personal Robotics Assistant

- [ ] Seamless digital + physical task execution
- [ ] Multi-robot coordination
- [ ] Web/mobile companion app
- [ ] Robust safety & failure handling

---

Contributions to any phase are welcome — see
[CONTRIBUTING.md](../CONTRIBUTING.md).
