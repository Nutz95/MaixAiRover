/**
 * Accumulate Stream bytes into LF-terminated command lines.
 */
#pragma once

#include <Arduino.h>
#include <stddef.h>

#include "settings.h"

class CommandDispatcher;
class ProtocolReply;

class SerialLineReader {
 public:
  /**
   * Read available bytes from ``stream`` and dispatch complete lines.
   * Used for USB Serial and MaixCAM UART.
   */
  void poll(Stream &stream, CommandDispatcher &dispatcher, ProtocolReply &reply);

 private:
  char lineBuf_[RoverSettings::kLineBufferSize];
  size_t lineLen_ = 0;
};
