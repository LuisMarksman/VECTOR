// Copy this file to `config.h` and fill in your values.
// `config.h` is git-ignored (see the repo-root .gitignore rules for secrets).
#pragma once

// ---- WiFi ---------------------------------------------------------------
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

// ---- MQTT (the VECTOR server's broker) ----------------------------------
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define MQTT_USER ""      // leave empty if the broker is open
#define MQTT_PASSWORD ""

// ---- Device identity ----------------------------------------------------
// Topics become:  vector/home/<DEVICE_ID>/set  and  .../state
#define BASE_TOPIC "vector"
#define DEVICE_ID "living-room-lamp"

// ---- Pins ---------------------------------------------------------------
#define RELAY_PIN 26   // drives a relay / MOSFET (the "light")
#define BUTTON_PIN 0   // optional manual toggle button (active-low)
