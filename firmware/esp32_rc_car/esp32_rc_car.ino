/*
 * VECTOR - ESP32 RC Car (4WD)
 * ---------------------------------------------------------------
 * Board : ESP32-DevKit-V1 (ESP32-WROOM-32)
 * Motors: 4x 12V DC geared motor, 100 RPM, 70 mm wheel
 * Drive : Skid-steer (tank drive) - left pair + right pair
 *
 * Two L298N motor drivers, each driving 2 motors:
 *
 *   Driver 1  (FRONT)
 *     Channel A (OUT1/OUT2) -> FRONT RIGHT motor   (OUT1 = motor GND wire, OUT2 = other)
 *     Channel B (OUT3/OUT4) -> FRONT LEFT  motor   (OUT4 = motor GND wire, OUT3 = other)
 *
 *   Driver 2  (BACK)
 *     Channel A (OUT1/OUT2) -> BACK  RIGHT motor   (OUT1 = motor GND wire, OUT2 = other)
 *     Channel B (OUT3/OUT4) -> BACK  LEFT  motor   (OUT4 = motor GND wire, OUT3 = other)
 *
 * Power : 4x 18650 in series (~14.8V nominal / 16.8V full charge)
 *         -> both L298N +12V terminals, motor supply.
 *         PWM keeps the average voltage the motors see near their 12V rating.
 *
 * Control: connect to WiFi AP "ESP32_RC_CAR" (pass 12345678), open http://192.168.4.1
 *
 * NOTE ON DIRECTION:
 *   The IN pins below are set so that each motor's NON-GND terminal is driven HIGH
 *   for "forward". Because the left/right motors are mounted mirror-image and are
 *   wired mirror-image (GND on OUT1 for the right motors, GND on OUT4 for the left
 *   motors), this makes the whole car roll forward. If any single wheel spins the
 *   wrong way, either swap that motor's two OUTx wires, or swap its IN-pin pair in
 *   the *_IN defines below.
 */

#include <WiFi.h>
#include <WebServer.h>

const char* ssid     = "ESP32_RC_CAR";
const char* password = "12345678";

WebServer server(80);

// ---------------- Pin map: ESP32-DevKit-V1 -> L298N ----------------
// Driver 1 (FRONT L298N)
#define FR_EN    13   // ENA  (PWM front-right)
#define FR_INP   27   // IN2  -> OUT2 (front-right + / non-GND terminal)
#define FR_INN   14   // IN1  -> OUT1 (front-right GND wire)
#define FL_EN    26   // ENB  (PWM front-left)
#define FL_INP   25   // IN3  -> OUT3 (front-left + / non-GND terminal)
#define FL_INN   33   // IN4  -> OUT4 (front-left GND wire)

// Driver 2 (BACK L298N)
#define BR_EN    32   // ENA  (PWM back-right)
#define BR_INP   22   // IN2  -> OUT2 (back-right + / non-GND terminal)
#define BR_INN   23   // IN1  -> OUT1 (back-right GND wire)
#define BL_EN    21   // ENB  (PWM back-left)
#define BL_INP   19   // IN3  -> OUT3 (back-left + / non-GND terminal)
#define BL_INN   18   // IN4  -> OUT4 (back-left GND wire)

// PWM config (8-bit -> duty 0..255). 200 ~= 78% keeps a ~16V pack near the 12V rating.
// ESP32 core 2.x uses channel-based LEDC: one channel per EN pin.
const int   PWM_FREQ = 1000;
const int   PWM_RES  = 8;
int         motorSpeed = 200;

#define FR_CH 0   // LEDC channel for front-right EN
#define FL_CH 1   // LEDC channel for front-left  EN
#define BR_CH 2   // LEDC channel for back-right  EN
#define BL_CH 3   // LEDC channel for back-left   EN

// ---------------- Low level motor control ----------------
// dir: +1 forward (drive the + terminal HIGH), -1 reverse, 0 = coast/stop
void driveMotor(int enCh, int inPos, int inNeg, int dir, int speed) {
  if (dir > 0) {           // forward
    digitalWrite(inPos, HIGH);
    digitalWrite(inNeg, LOW);
    ledcWrite(enCh, speed);
  } else if (dir < 0) {    // reverse
    digitalWrite(inPos, LOW);
    digitalWrite(inNeg, HIGH);
    ledcWrite(enCh, speed);
  } else {                 // stop
    digitalWrite(inPos, LOW);
    digitalWrite(inNeg, LOW);
    ledcWrite(enCh, 0);
  }
}

void frontRight(int dir) { driveMotor(FR_CH, FR_INP, FR_INN, dir, motorSpeed); }
void frontLeft (int dir) { driveMotor(FL_CH, FL_INP, FL_INN, dir, motorSpeed); }
void backRight (int dir) { driveMotor(BR_CH, BR_INP, BR_INN, dir, motorSpeed); }
void backLeft  (int dir) { driveMotor(BL_CH, BL_INP, BL_INN, dir, motorSpeed); }

void rightSide(int dir) { frontRight(dir); backRight(dir); }
void leftSide (int dir) { frontLeft(dir);  backLeft(dir);  }

// ---------------- Movements (skid-steer) ----------------
void moveForward()  { leftSide(+1); rightSide(+1); }
void moveBackward() { leftSide(-1); rightSide(-1); }
void turnLeft()     { leftSide(-1); rightSide(+1); }   // pivot left
void turnRight()    { leftSide(+1); rightSide(-1); }   // pivot right
void stopMotors()   { leftSide(0);  rightSide(0);  }

// ---------------- Web UI ----------------
const char webpage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#111;color:white;text-align:center;font-family:Arial;}
button{width:120px;height:90px;font-size:30px;margin:10px;border-radius:15px;
       -webkit-user-select:none;user-select:none;touch-action:manipulation;}
</style>
</head>
<body>
<h2>VECTOR - ESP32 RC Car (4WD)</h2>

<button ontouchstart="fetch('/forward')"  ontouchend="fetch('/stop')"
        onmousedown="fetch('/forward')"    onmouseup="fetch('/stop')">&#11014;</button>
<br>
<button ontouchstart="fetch('/left')"      ontouchend="fetch('/stop')"
        onmousedown="fetch('/left')"        onmouseup="fetch('/stop')">&#11013;</button>
<button onclick="fetch('/stop')">&#9632;</button>
<button ontouchstart="fetch('/right')"     ontouchend="fetch('/stop')"
        onmousedown="fetch('/right')"       onmouseup="fetch('/stop')">&#10145;</button>
<br>
<button ontouchstart="fetch('/backward')"  ontouchend="fetch('/stop')"
        onmousedown="fetch('/backward')"    onmouseup="fetch('/stop')">&#11015;</button>
</body>
</html>
)rawliteral";

void setup() {
  Serial.begin(115200);

  int inPins[] = { FR_INP, FR_INN, FL_INP, FL_INN,
                   BR_INP, BR_INN, BL_INP, BL_INN };
  for (int p : inPins) pinMode(p, OUTPUT);

  // LEDC (core 2.x): configure a channel, then bind it to the EN pin.
  int enPins[]     = { FR_EN, FL_EN, BR_EN, BL_EN };
  int enChannels[] = { FR_CH, FL_CH, BR_CH, BL_CH };
  for (int i = 0; i < 4; i++) {
    ledcSetup(enChannels[i], PWM_FREQ, PWM_RES);
    ledcAttachPin(enPins[i], enChannels[i]);
  }

  stopMotors();

  WiFi.softAP(ssid, password);
  Serial.println();
  Serial.println("WiFi Started");
  Serial.print("Connect to: ");   Serial.println(ssid);
  Serial.print("Open: http://");  Serial.println(WiFi.softAPIP());

  server.on("/",         []() { server.send(200, "text/html", webpage); });
  server.on("/forward",  []() { moveForward();  server.send(200, "text/plain", "OK"); });
  server.on("/backward", []() { moveBackward(); server.send(200, "text/plain", "OK"); });
  server.on("/left",     []() { turnLeft();     server.send(200, "text/plain", "OK"); });
  server.on("/right",    []() { turnRight();    server.send(200, "text/plain", "OK"); });
  server.on("/stop",     []() { stopMotors();   server.send(200, "text/plain", "OK"); });

  server.begin();
  Serial.println("Web Server Started");
}

void loop() {
  server.handleClient();
}
