#include "protocol_reply.h"

#include <stdio.h>

#include "settings.h"
#include "wifi_console.h"

void ProtocolReply::setOut(Stream &out) {
  out_ = &out;
}

void ProtocolReply::ok(const char *msg) const {
  emit("OK ", msg);
}

void ProtocolReply::err(const char *msg) const {
  emit("ERR ", msg);
}

void ProtocolReply::emit(const char *prefix, const char *msg) const {
  Stream *out = (out_ != nullptr) ? out_ : &Serial;
  out->print(prefix);
  out->println(msg);
  out->flush();
  char buf[RoverSettings::kReplyBufferSize];
  snprintf(buf, sizeof(buf), "%s%s", prefix, msg);
  WifiConsole::println(buf);
}
