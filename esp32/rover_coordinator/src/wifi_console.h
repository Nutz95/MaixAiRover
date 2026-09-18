/**
 * Minimal TCP console on WiFi (port 2333). Same line protocol as USB Serial.
 */

#pragma once

#include <Arduino.h>
#include <stdint.h>

namespace WifiConsole {

using LineHandler = void (*)(char *line);

void setLineHandler(LineHandler handler);
void begin(uint16_t port = 2333);
void poll();
void println(const char *msg);
bool clientConnected();

}
