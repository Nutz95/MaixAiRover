#include "protocol_reply.h"

#include <Arduino.h>
#include <stdio.h>

#include "settings.h"
#include "wifi_console.h"

void ProtocolReply::ok(const char *msg) const {
  emit("OK ", msg);
}

void ProtocolReply::err(const char *msg) const {
  emit("ERR ", msg);
}

void ProtocolReply::emit(const char *prefix, const char *msg) const {
  Serial.print(prefix);
  Serial.println(msg);
  Serial.flush();
  char buf[RoverSettings::kReplyBufferSize];
  snprintf(buf, sizeof(buf), "%s%s", prefix, msg);
  WifiConsole::println(buf);
}
