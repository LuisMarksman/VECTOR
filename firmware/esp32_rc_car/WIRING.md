# ESP32 RC Car (4WD) — Wiring

Board: **ESP32-DevKit-V1** · 4× 12V DC geared motor (100 RPM, 70 mm wheel) ·
2× **L298N** motor drivers · Battery: **4× 18650 in series** (~14.8V nom / 16.8V full).

## Motor → L298N mapping

| L298N        | Channel        | Motor        | Motor GND wire | Other wire |
|--------------|----------------|--------------|----------------|------------|
| Driver 1 (FRONT) | A (OUT1/OUT2) | Front Right | OUT1           | OUT2       |
| Driver 1 (FRONT) | B (OUT3/OUT4) | Front Left  | OUT4           | OUT3       |
| Driver 2 (BACK)  | A (OUT1/OUT2) | Back Right  | OUT1           | OUT2       |
| Driver 2 (BACK)  | B (OUT3/OUT4) | Back Left   | OUT4           | OUT3       |

## ESP32-DevKit-V1 → L298N control pins

### Driver 1 (FRONT)
| L298N pin | Function            | ESP32 GPIO |
|-----------|---------------------|------------|
| ENA       | PWM, front-right    | **GPIO 13** |
| IN1       | front-right dir     | **GPIO 14** |
| IN2       | front-right dir     | **GPIO 27** |
| ENB       | PWM, front-left     | **GPIO 26** |
| IN3       | front-left dir      | **GPIO 25** |
| IN4       | front-left dir      | **GPIO 33** |

### Driver 2 (BACK)
| L298N pin | Function           | ESP32 GPIO |
|-----------|--------------------|------------|
| ENA       | PWM, back-right    | **GPIO 32** |
| IN1       | back-right dir     | **GPIO 23** |
| IN2       | back-right dir     | **GPIO 22** |
| ENB       | PWM, back-left     | **GPIO 21** |
| IN3       | back-left dir      | **GPIO 19** |
| IN4       | back-left dir      | **GPIO 18** |

> Remove the **ENA/ENB jumpers** on both L298N boards so the ESP32 can control
> speed via PWM on those pins.

## Power & ground

```
4x 18650 (series) + ── L298N #1  +12V ─┬─ L298N #2  +12V
                  - ── L298N #1  GND  ─┴─ L298N #2  GND ── ESP32 GND (common ground!)
```

- Battery **+** → the **+12V** terminal of **both** L298N boards.
- Battery **–** → the **GND** terminal of **both** L298N boards.
- **Tie all grounds together**: both L298N GND ↔ **ESP32 GND**. Without a common
  ground the IN/EN logic signals have no reference and the motors behave randomly.
- Powering the ESP32:
  - Easiest: give the ESP32 its own 5V (USB power bank or a small buck converter
    from the pack down to 5V into the `VIN`/`5V` pin), **plus the shared GND**.
  - The L298N onboard 5V regulator can power the ESP32 **only** if the `5V-EN`
    jumper is set and the pack is ≤ ~12V. With a ~16.8V pack that regulator runs
    hot and is not recommended — use a separate buck/USB supply instead.
- Do **not** power the ESP32 from a 3.3V pin for the logic; the L298N INx inputs
  accept the ESP32's 3.3V logic levels fine as inputs.

## Direction check (first run)

Each motor is driven so its **non-GND terminal goes HIGH for "forward"**, which —
given the mirror wiring above — should roll the car forward. On first test, lift
the wheels off the ground and press **Forward**:

- If a single wheel spins backward → swap that motor's two `OUTx` wires
  (or swap its IN-pin pair in the sketch).
- If the whole car turns instead of going straight → the two sides are reversed
  relative to each other; flip one side.

## Control

Connect to WiFi **`ESP32_RC_CAR`** (password `12345678`), then open
**http://192.168.4.1** — arrows for forward/back, left/right pivot, ■ to stop.
Default speed is PWM 200/255 (~78%); edit `motorSpeed` in the sketch to change it.
