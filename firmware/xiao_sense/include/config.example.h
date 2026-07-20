// Copy this file to `config.h` and fill in your values.
#pragma once

// ---- WiFi ---------------------------------------------------------------
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

// ---- MQTT (the VECTOR server's broker) ----------------------------------
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define MQTT_USER ""
#define MQTT_PASSWORD ""

// ---- Device identity ----------------------------------------------------
// Reports to:  vector/home/<DEVICE_ID>/state
#define BASE_TOPIC "vector"
#define DEVICE_ID "hallway-motion"

// ---- Pins ---------------------------------------------------------------
#define PIR_PIN 2          // motion sensor (digital)
#define REPORT_INTERVAL_MS 10000  // heartbeat interval
