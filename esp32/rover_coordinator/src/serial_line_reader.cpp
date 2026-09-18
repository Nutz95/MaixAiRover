#include "serial_line_reader.h"

#include <Arduino.h>

#include "command_dispatcher.h"
#include "protocol_reply.h"

void SerialLineReader::poll(CommandDispatcher &dispatcher, ProtocolReply &reply) {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      lineBuf_[lineLen_] = '\0';
      dispatcher.handleLine(lineBuf_);
      lineLen_ = 0;
      continue;
    }
    if (lineLen_ + 1 < sizeof(lineBuf_)) {
      lineBuf_[lineLen_++] = c;
    } else {
      lineLen_ = 0;
      reply.err("line too long");
    }
  }
}
