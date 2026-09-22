#include "wifi_console.h"

#include <WiFi.h>

#include "settings.h"

namespace WifiConsole {
namespace {

WiFiServer *server = nullptr;
WiFiClient client;
uint16_t listenPort = RoverSettings::kWifiConsolePort;
bool started = false;
char lineBuf[RoverSettings::kLineBufferSize];
size_t lineLen = 0;
LineHandler handler = nullptr;

}  // namespace

void setLineHandler(LineHandler h) {
  handler = h;
}

void begin(uint16_t port) {
  if (started) {
    return;
  }
  listenPort = port;
  server = new WiFiServer(listenPort);
  server->begin();
  started = true;
  Serial.printf("wifi-console: listening on :%u\n", (unsigned)listenPort);
}

bool clientConnected() {
  return client && client.connected();
}

void println(const char *msg) {
  if (clientConnected()) {
    client.println(msg);
  }
}

static void pollClientRx() {
  if (!clientConnected() || handler == nullptr) {
    return;
  }
  while (client.available() > 0) {
    char c = (char)client.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      lineBuf[lineLen] = '\0';
      if (lineLen > 0) {
        handler(lineBuf);
      }
      lineLen = 0;
      continue;
    }
    if (lineLen + 1 < sizeof(lineBuf)) {
      lineBuf[lineLen++] = c;
    } else {
      lineLen = 0;
    }
  }
}

void poll() {
  if (!started || server == nullptr) {
    return;
  }
  if (!client || !client.connected()) {
    WiFiClient incoming = server->available();
    if (incoming) {
      client = incoming;
      client.println(
        "MaixAiRover ESP console - text: PING INIT STOP SPEED PWM BAT ENC WIFI SCAN HELP | "
        "bin: SYNC=0xA5");
      Serial.println("wifi-console: client connected");
    }
  }
  pollClientRx();
}

}  // namespace WifiConsole
