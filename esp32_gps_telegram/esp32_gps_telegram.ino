/*
 * ESP32 GPS -> Telegram Bot
 * ------------------------------------------------------------
 * Board : ESP32 DevKit v1 (esp32dev)
 * GPS   : NEO-6M (GY-GPS6MV2)
 *
 * Sends the current GPS location to a Telegram chat, either
 * periodically or when you send "/location" to the bot.
 *
 * Wiring (GPS  ->  ESP32):
 *   GPS VCC  ->  3.3V   (do NOT use 5V on most modules)
 *   GPS GND  ->  GND
 *   GPS TX   ->  GPIO16 (ESP32 RX2)
 *   GPS RX   ->  GPIO17 (ESP32 TX2)
 *
 * Libraries to install via Arduino Library Manager:
 *   - TinyGPSPlus            (by Mikal Hart)
 *   - UniversalTelegramBot   (by Brian Lough)
 *   - ArduinoJson            (v6.x, dependency of the bot lib)
 *
 * Board support: install "esp32 by Espressif Systems" in the
 * Boards Manager, then select "DOIT ESP32 DEVKIT V1".
 * ------------------------------------------------------------
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <UniversalTelegramBot.h>
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

// ------------------- USER CONFIGURATION ---------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Get this from @BotFather when you create your bot.
#define BOT_TOKEN "YOUR_TELEGRAM_BOT_TOKEN"

// Your chat ID. Send a message to your bot, then visit:
//   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
// and read the "chat":{"id": ...} value.
#define CHAT_ID  "YOUR_CHAT_ID"

// Send location automatically every N milliseconds (0 = disabled,
// only respond to /location commands). Default: every 60 seconds.
const unsigned long SEND_INTERVAL_MS = 60000UL;
// ------------------------------------------------------------

// GPS on UART2 (Serial2): RX=GPIO16, TX=GPIO17
#define GPS_RX_PIN 16   // connect to GPS TX
#define GPS_TX_PIN 17   // connect to GPS RX
#define GPS_BAUD   9600

TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

WiFiClientSecure secured_client;
UniversalTelegramBot bot(BOT_TOKEN, secured_client);

unsigned long lastSendTime = 0;
unsigned long lastBotCheck = 0;
const unsigned long BOT_CHECK_INTERVAL_MS = 1000;  // poll Telegram every 1s

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected. IP: ");
  Serial.println(WiFi.localIP());
}

// Read available GPS bytes and feed them into the parser.
void feedGPS() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }
}

String buildLocationMessage() {
  if (gps.location.isValid()) {
    double lat = gps.location.lat();
    double lng = gps.location.lng();

    String msg = "\xF0\x9F\x93\x8D Location fix\n";  // 📍 emoji
    msg += "Lat: " + String(lat, 6) + "\n";
    msg += "Lng: " + String(lng, 6) + "\n";

    if (gps.altitude.isValid()) {
      msg += "Alt: " + String(gps.altitude.meters(), 1) + " m\n";
    }
    if (gps.speed.isValid()) {
      msg += "Speed: " + String(gps.speed.kmph(), 1) + " km/h\n";
    }
    if (gps.satellites.isValid()) {
      msg += "Satellites: " + String(gps.satellites.value()) + "\n";
    }
    // Clickable Google Maps link.
    msg += "https://maps.google.com/?q=" + String(lat, 6) + "," + String(lng, 6);
    return msg;
  }
  return "";  // no valid fix yet
}

void sendLocation(const String& chatId) {
  String msg = buildLocationMessage();
  if (msg.length() > 0) {
    bot.sendMessage(chatId, msg, "");
    Serial.println("Sent location to " + chatId);
  } else {
    bot.sendMessage(chatId,
      "\xE2\x9A\xA0\xEF\xB8\x8F No GPS fix yet. Make sure the module has a "
      "clear view of the sky and wait for it to lock on.", "");
    Serial.println("No valid GPS fix to send.");
  }
}

// Handle incoming Telegram messages.
void handleNewMessages(int numNewMessages) {
  for (int i = 0; i < numNewMessages; i++) {
    String chat_id = bot.messages[i].chat_id;
    String text    = bot.messages[i].text;
    text.trim();

    if (text == "/location" || text == "/start" || text == "/loc") {
      sendLocation(chat_id);
    } else {
      bot.sendMessage(chat_id,
        "Send /location to get the current GPS position.", "");
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("GPS serial started.");

  connectWiFi();

  // Telegram uses TLS. Trust Telegram's root CA.
  secured_client.setCACert(TELEGRAM_CERTIFICATE_ROOT);

  Serial.println("Setup complete. Waiting for GPS fix...");
}

void loop() {
  feedGPS();  // keep parsing GPS data continuously

  unsigned long now = millis();

  // Poll Telegram for new messages.
  if (now - lastBotCheck > BOT_CHECK_INTERVAL_MS) {
    int numNew = bot.getUpdates(bot.last_message_received + 1);
    while (numNew) {
      handleNewMessages(numNew);
      numNew = bot.getUpdates(bot.last_message_received + 1);
    }
    lastBotCheck = now;
  }

  // Periodic automatic sending.
  if (SEND_INTERVAL_MS > 0 && (now - lastSendTime > SEND_INTERVAL_MS)) {
    if (gps.location.isValid()) {
      sendLocation(CHAT_ID);
    } else {
      Serial.println("Interval reached but no GPS fix yet.");
    }
    lastSendTime = now;
  }
}
