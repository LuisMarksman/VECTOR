<div align="center">

#  VECTOR

### Virtual Engine for Control, Tasks & Operational Robotics

### The Complete Personal Robotics & AI Assistant


---

![Status](https://img.shields.io/badge/Status-In%20Development-orange)

![License](https://img.shields.io/badge/License-MIT-blue)

</div>

---

#  Introduction

VECTOR (**Virtual Engine for Control, Tasks & Operational Robotics**) is an open Personal Robotics and Artificial Intelligence platform designed to bridge the gap between digital intelligence and the physical world.

Unlike traditional voice assistants that simply answer questions, VECTOR is designed to **understand, reason, plan, and act**.

It combines conversational AI, computer vision, smart home automation, autonomous mobile robots, robotic manipulation, and intelligent software agents into a unified ecosystem capable of assisting users in their everyday lives.

The long-term vision is to build a complete Personal Robotics Operating System capable of becoming an intelligent companion for homes, workplaces, and future autonomous environments.

---

#  Vision

Current AI assistants can answer questions.

VECTOR aims to go beyond conversation.

Imagine saying:

> "VECTOR, clean the living room, remind me to call Mom after dinner, and bring me my water bottle."

Instead of only replying, VECTOR can:

- Understand your request
- Break it into multiple tasks
- Plan the execution
- Control smart home devices
- Navigate autonomous robots
- Operate robotic manipulators
- Notify you when everything is completed

VECTOR is designed to become an intelligent system that manages both **digital tasks** and **physical tasks** through natural interaction.

---

#  Core Capabilities

##  Personal AI Assistant

- Natural voice conversations
- Long-term memory
- Context awareness
- Multi-step reasoning
- Agentic task execution
- Calendar management
- Reminder management
- Email assistance
- Messaging
- Internet search
- Daily planning

---

##  Smart Home

- Home automation
- Appliance control
- Smart lighting
- Smart switches
- CCTV integration
- Security monitoring
- Sensor monitoring
- Energy monitoring

---

##  Computer Vision

- Object detection
- Face recognition
- Person tracking
- OCR
- Gesture recognition
- Scene understanding

---

##  Robotics

- Autonomous mobile robot
- Robot arm manipulation
- Pick and place
- Object delivery
- Vacuum cleaning
- Autonomous navigation
- Multi-robot coordination

---

##  AI Server

VECTOR's intelligence runs through a central AI server responsible for:

- Task planning
- AI reasoning
- Long-term memory
- Device orchestration
- Robot coordination
- Home automation
- API services
- Multi-agent communication

---

#  System Architecture

```text
                   USER

                     │

          Voice │ Mobile │ Web

                     │

            ┌────────▼────────┐
            │   VECTOR Server │
            ├─────────────────┤
            │ AI Agent        │
            │ Memory          │
            │ Planner         │
            │ Robot Manager   │
            │ Home Automation │
            └────────┬────────┘
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼

 Smart Home      Robot Arm     Mobile Robot

 Lights          Pick & Place  Navigation

 CCTV            Manipulation  Vacuum

 Sensors                         Delivery
```

---

#  Hardware

Current development includes:

- Raspberry Pi
- Arduino Q
- ESP32
- XIAO Sense
- AI Server
- Autonomous Mobile Robot
- Robot Arm
- Cameras
- Microphones
- Speakers
- Servo Motors
- Environmental Sensors

---

#  Software Stack

## AI

- Large Language Models
- Agentic AI
- Computer Vision
- Speech Recognition
- Text-to-Speech

## Backend

- Python
- FastAPI
- MQTT
- Docker

## Robotics

- ROS2
- OpenCV

## Embedded

- ESP-IDF
- Arduino Framework

---

#  Development Status

VECTOR is currently under active development.

## Current Focus

- Voice Assistant
- AI Server
- Mobile Robot
- Home Automation
- Robot Arm Integration

Future releases will expand the platform into a complete Personal Robotics ecosystem.

---

#  Quick Start

Get the VECTOR brain running locally — **no hardware or API keys required**. It
ships with offline-friendly mock backends so the whole stack runs out of the box.

```bash
git clone https://github.com/LuisMarksman/VECTOR.git
cd VECTOR
make env            # create .env from the template
make setup          # install server + voice + vision dependencies
make server         # start the API at http://localhost:8000
```

Ask VECTOR to do something:

```bash
curl -X POST http://localhost:8000/assistant/command \
  -H 'content-type: application/json' \
  -d '{"text": "turn on the living room lights and vacuum the floor"}'
```

VECTOR plans the request, splits it into steps, routes each to the right
capability (home automation, mobile robot, arm, …) and acts on it.

Prefer containers? `make up` starts the MQTT broker and server with Docker. See
**[docs/getting-started.md](docs/getting-started.md)** for the full walkthrough
and **[docs/architecture.md](docs/architecture.md)** for how it all fits together.

---

#  Repository Structure

```text
VECTOR/
├── server/          # FastAPI AI server — the reasoning & orchestration brain
├── voice/           # Voice assistant: wake word → STT → server → TTS
├── vision/          # Computer vision: detection, faces, tracking, OCR
├── robotics/        # ROS2 packages: mobile base, arm, perception, MQTT bridge
├── firmware/        # ESP32 / XIAO Sense embedded nodes (PlatformIO)
├── integrations/    # MQTT broker config + smart-home bridges
├── hardware/        # Bill of materials & wiring notes
├── docs/            # Architecture, getting-started, MQTT contract, roadmap
├── assets/          # Logos, diagrams, media
├── docker-compose.yml
├── Makefile
└── README.md
```

Each top-level directory is an independent component that communicates over the
MQTT message bus and the server's HTTP API. Start with
[docs/architecture.md](docs/architecture.md) to see how they connect.

---

#  Open Source

VECTOR integrates several open-source technologies while contributing original software, integrations, and system architecture.

Each third-party project remains under its original license.

See the acknowledgements for more information.

---

#  License

This project is released under the MIT License.

---

<div align="center">

##  VECTOR

### Building the future of Personal Robotics.


</div>
