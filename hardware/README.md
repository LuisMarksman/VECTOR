# VECTOR Hardware

Reference hardware for building VECTOR. Everything here is a starting point —
mix and match for your budget and goals. Quantities assume one mobile robot with
an arm plus a couple of smart-home nodes.

## System overview

```
   ┌──────────────┐        WiFi / MQTT        ┌─────────────────┐
   │  AI Server   │◄─────────────────────────►│  Smart-home nodes│
   │ (PC / Pi 5)  │                            │  (ESP32 / XIAO)  │
   └──────┬───────┘                            └─────────────────┘
          │ WiFi / MQTT
   ┌──────▼───────────────────────────────┐
   │        Mobile robot (Raspberry Pi)     │
   │  ┌───────────┐  ┌────────┐  ┌───────┐ │
   │  │ Motor ESP │  │  Arm   │  │Camera │ │
   │  │  + wheels │  │ servos │  │ (eye) │ │
   │  └───────────┘  └────────┘  └───────┘ │
   └────────────────────────────────────────┘
```

## Bill of materials

### Compute
| Item | Notes |
|------|-------|
| AI server | Any x86 PC, or a Raspberry Pi 5 (8 GB) for a compact setup |
| Raspberry Pi 4/5 | On-robot compute running ROS2 |
| ESP32 dev board | Low-level motor/IO controller & smart-home nodes |
| Seeed XIAO ESP32S3 Sense | Tiny camera + mic + sensor node |

### Mobile base
| Item | Notes |
|------|-------|
| Robot chassis | 2WD/4WD with DC gear motors + caster |
| Motor driver | TB6612FNG or L298N (H-bridge) |
| Wheel encoders | For odometry (optional but recommended) |
| LiDAR | RPLIDAR A1 for mapping/Nav2 (optional) |
| Battery | 3S Li-ion pack + BMS, plus a buck converter (5 V) |

### Manipulation
| Item | Notes |
|------|-------|
| Robot arm | 4–6 DOF servo arm |
| Servos | MG996R / high-torque digital servos |
| Servo driver | PCA9685 16-channel PWM (I²C) |
| Gripper | Parallel or soft gripper |

### Perception & audio
| Item | Notes |
|------|-------|
| Camera | USB / CSI camera, or the XIAO Sense camera (the "eye") |
| Microphone | USB mic or I²S MEMS mic for the voice front-end |
| Speaker | Small amplified speaker for TTS |

### Smart home
| Item | Notes |
|------|-------|
| Relay module | Switch mains lighting/appliances (observe safety!) |
| PIR sensor | Motion detection |
| Environmental sensor | e.g. DHT22 / BME280 |

## Wiring notes

- **ESP32 relay node** — relay IN → `RELAY_PIN` (GPIO 26 by default), plus 5 V
  and GND. Optional manual button on `BUTTON_PIN` (GPIO 0, active-low). Pin map
  lives in `firmware/esp32_node/include/config.h`.
- **XIAO Sense sensor node** — PIR OUT → `PIR_PIN` (GPIO 2). See
  `firmware/xiao_sense/include/config.h`.
- **Arm** — servos → PCA9685 channels; PCA9685 SDA/SCL → the Pi's I²C; power the
  servos from a separate 5–6 V rail (not the Pi's 5 V).
- **Motors** — driver inputs → ESP32/Pi GPIO; motor power from the battery rail,
  common ground with logic.

> ⚠️ **Mains safety:** switching mains voltage with relays is dangerous. Use
> properly rated, enclosed relay modules and have mains work checked by someone
> qualified. When in doubt, switch smart plugs over MQTT instead.

## Add your own

Drop schematics, wiring diagrams, and STL/CAD files here (e.g. `hardware/cad/`,
`hardware/schematics/`) and link them from this page.
