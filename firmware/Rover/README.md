# Rover — ESP32 4WD RC Car (Prototype)

Part of the **VECTOR** personal robotics platform. Rover is the mobile-robot
base: an ESP32-DevKit-V1 driving four 12V geared motors (100 RPM, 70 mm wheels)
through two L298N drivers, controlled over WiFi from a phone/browser.

## Prototype demonstration

https://github.com/LuisMarksman/VECTOR/raw/claude/esp32-rc-car-web-6ieiev/firmware/Rover/media/prototype_demo.mp4

<video src="https://github.com/LuisMarksman/VECTOR/raw/claude/esp32-rc-car-web-6ieiev/firmware/Rover/media/prototype_demo.mp4" controls muted></video>

> ▶ If the player above doesn't load, [click here to watch the demo](media/prototype_demo.mp4).

## Status — work in progress 🚧

This is only the first prototype. It proves out the drivetrain and remote
control; it is **not** the final robot. The build is still in progress, and
from here we plan to:

- **Build a better chassis** — a sturdier, purpose-designed frame to replace the prototype base.
- **Attach robot arm(s)** — for pick-and-place and object manipulation.
- **Add a camera** — onboard vision for perception.
- **Add a Vision-Action model** — so Rover can perceive its surroundings and act on its own, making it **autonomous**.
- **Add a voice assistant** — integrate VECTOR's voice layer so Rover can be **voice controlled**.

Together these turn this simple RC prototype into an autonomous, voice-controlled
mobile robot within the VECTOR ecosystem.

## Files

| File | Description |
|------|-------------|
| [`Rover.ino`](Rover.ino) | ESP32 sketch — WiFi AP + web control, skid-steer over two L298N drivers |
| [`WIRING.md`](WIRING.md) | Full wiring: motors → L298N and L298N → ESP32, power, and first-run direction check |

## Quick start

1. Flash `Rover.ino` (Arduino IDE, board **ESP32 Dev Module**, ESP32 core 2.x).
2. Wire everything per [`WIRING.md`](WIRING.md).
3. Power on, connect to WiFi **`ESP32_RC_CAR`** (password `12345678`).
4. Open **http://192.168.4.1** and drive.
