// VECTOR ESP32 node
// -----------------------------------------------------------------------------
// A smart-home actuator that plugs straight into the VECTOR server's MQTT bus.
// It listens on   vector/home/<DEVICE_ID>/set   for commands like {"action":"on"}
// and reports its state (retained) on   vector/home/<DEVICE_ID>/state .
// The server's HomeAutomation service (see server/app/core/home_automation.py)
// speaks exactly this contract, so no extra glue is needed.
// -----------------------------------------------------------------------------
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "config.h"

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String setTopic;
String stateTopic;
bool relayState = false;

void publishState() {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["kind"] = "light";
  doc["online"] = true;
  doc["state"]["power"] = relayState ? "on" : "off";

  char buffer[256];
  size_t n = serializeJson(doc, buffer);
  mqtt.publish(stateTopic.c_str(), buffer, n);  // retained below in reconnect
}

void applyState(bool on) {
  relayState = on;
  digitalWrite(RELAY_PIN, on ? HIGH : LOW);
  publishState();
  Serial.printf("relay -> %s\n", on ? "ON" : "OFF");
}

void onMessage(char* topic, byte* payload, unsigned int length) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, length)) {
    Serial.println("ignoring malformed command");
    return;
  }
  const char* action = doc["action"] | "";
  if (strcmp(action, "on") == 0) {
    applyState(true);
  } else if (strcmp(action, "off") == 0) {
    applyState(false);
  } else if (strcmp(action, "toggle") == 0) {
    applyState(!relayState);
  }
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
    // Last-will marks the device offline if it drops unexpectedly.
    String willPayload = String("{\"device_id\":\"") + DEVICE_ID + "\",\"online\":false}";
    bool ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD,
                           stateTopic.c_str(), 0, true, willPayload.c_str());
    if (ok) {
      Serial.println(" connected");
      mqtt.subscribe(setTopic.c_str());
      publishState();
    } else {
      Serial.printf(" failed (rc=%d), retrying\n", mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(RELAY_PIN, LOW);

  setTopic = String(BASE_TOPIC) + "/home/" + DEVICE_ID + "/set";
  stateTopic = String(BASE_TOPIC) + "/home/" + DEVICE_ID + "/state";

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  // Optional manual toggle button (debounced).
  static uint32_t lastPress = 0;
  if (digitalRead(BUTTON_PIN) == LOW && millis() - lastPress > 300) {
    lastPress = millis();
    applyState(!relayState);
  }
}
