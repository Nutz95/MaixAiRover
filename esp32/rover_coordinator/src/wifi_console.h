/**
 * Minimal TCP console on WiFi. Same line protocol as USB Serial.
 */

#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "settings.h"

namespace WifiConsole {

using LineHandler = void (*)(char *line);

void setLineHandler(LineHandler handler);
void begin(uint16_t port = RoverSettings::kWifiConsolePort);
void poll();
void println(const char *msg);
bool clientConnected();

}
