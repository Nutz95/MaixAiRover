/**
 * Optional WiFi STA join, ArduinoOTA, and TCP console lifecycle.
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

class WifiRuntime {
 public:
  /** Begin background STA join when SSID is configured. */
  void beginBackground();

  /** Poll connection, start OTA/console once, then service them. */
  void poll();

  /** True when STA has an IP. */
  bool isConnected() const;

  /** Fill buf with dotted IPv4 when connected; otherwise false. */
  bool localIp(char *buf, size_t buflen) const;

 private:
  bool wifiStarted_ = false;
  bool otaReady_ = false;
  uint32_t lastWifiLogMs_ = 0;
};
