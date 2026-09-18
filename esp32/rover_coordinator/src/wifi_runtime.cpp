#include "wifi_runtime.h"

#include <Arduino.h>
#include <ArduinoOTA.h>
#include <WiFi.h>
#include <stdio.h>
#include <string.h>

#include "settings.h"
#include "wifi_console.h"
#include "wifi_secrets.h"

void WifiRuntime::beginBackground() {
  if (WIFI_SSID[0] == '\0') {
    Serial.println("wifi: skipped (no SOARM_WIFI_SSID) - USB flash only");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  wifiStarted_ = true;
  Serial.printf("wifi: joining %s in background (OTA/console optional)\n", WIFI_SSID);
}

void WifiRuntime::poll() {
  if (!wifiStarted_) {
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    if (!otaReady_ && (millis() - lastWifiLogMs_) > RoverSettings::kWifiOfflineLogIntervalMs) {
      lastWifiLogMs_ = millis();
      Serial.println("wifi: still offline - coordinator OK without it");
    }
    return;
  }
  if (!otaReady_) {
    ArduinoOTA.setHostname(ARDUINO_OTA_HOSTNAME);
    ArduinoOTA.begin();
    WifiConsole::begin(RoverSettings::kWifiConsolePort);
    otaReady_ = true;
    Serial.print("wifi: OK ip=");
    Serial.println(WiFi.localIP());
    Serial.println("ota: ready (espota)");
    Serial.printf(
      "wifi-console: tcp %s:%u\n",
      WiFi.localIP().toString().c_str(),
      static_cast<unsigned>(RoverSettings::kWifiConsolePort));
  }
  ArduinoOTA.handle();
  WifiConsole::poll();
}

bool WifiRuntime::isConnected() const {
  return WiFi.status() == WL_CONNECTED;
}

bool WifiRuntime::localIp(char *buf, size_t buflen) const {
  if (!isConnected() || buf == nullptr || buflen == 0) {
    return false;
  }
  const String ip = WiFi.localIP().toString();
  strncpy(buf, ip.c_str(), buflen - 1);
  buf[buflen - 1] = '\0';
  return true;
}
