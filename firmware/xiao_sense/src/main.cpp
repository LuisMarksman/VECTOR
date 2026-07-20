// VECTOR XIAO ESP32S3 Sense node
// -----------------------------------------------------------------------------
// A battery-friendly wireless sensor. It reports motion (and a periodic
// heartbeat) to  vector/home/<DEVICE_ID>/state , feeding the server's sensor and
// security monitoring. The XIAO Sense also has a camera + microphone; see the
// note at the bottom for streaming frames to the vision worker.
// -----------------------------------------------------------------------------
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "config.h"

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String stateTopic;
bool lastMotion = false;
uint32_t lastReport = 0;

void publishState(bool motion) {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["kind"] = "sensor";
  doc["online"] = true;
  doc["state"]["motion"] = motion;
  doc["state"]["rssi"] = WiFi.RSSI();

  char buffer[256];
  size_t n = serializeJson(doc, buffer);
  mqtt.publish(stateTopic.c_str(), buffer, n, true);  // retained
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.printf("\nWiFi connected: %s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("connecting to MQTT...");
    String clientId = String("vector-") + DEVICE_ID;
    String willPayload = String("{\"device_id\":\"") + DEVICE_ID + "\",\"online\":false}";
    bool ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD,
                           stateTopic.c_str(), 0, true, willPayload.c_str());
    if (ok) {
      Serial.println(" connected");
      publishState(false);
    } else {
      Serial.printf(" failed (rc=%d), retrying\n", mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  stateTopic = String(BASE_TOPIC) + "/home/" + DEVICE_ID + "/state";

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  bool motion = digitalRead(PIR_PIN) == HIGH;
  if (motion != lastMotion) {
    lastMotion = motion;
    publishState(motion);
    Serial.printf("motion: %s\n", motion ? "detected" : "clear");
  }

  // Periodic heartbeat so the server knows the sensor is alive.
  if (millis() - lastReport > REPORT_INTERVAL_MS) {
    lastReport = millis();
    publishState(lastMotion);
  }
}

// -----------------------------------------------------------------------------
// Extending to the camera:
//   The XIAO ESP32S3 Sense has an OV2640 camera. To feed the vision pipeline,
//   initialise it with the `esp32-camera` driver and either (a) POST JPEG frames
//   to the server's vision worker, or (b) run an HTTP/RTSP stream that the
//   `vision` package consumes via VECTOR_CAMERA_SOURCE.
// -----------------------------------------------------------------------------
