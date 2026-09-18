/**
 * Accumulate USB Serial bytes into LF-terminated command lines.
 */
#pragma once

#include <stddef.h>

#include "settings.h"

class CommandDispatcher;
class ProtocolReply;

class SerialLineReader {
 public:
  /** Read available Serial bytes and dispatch complete lines. */
  void poll(CommandDispatcher &dispatcher, ProtocolReply &reply);

 private:
  char lineBuf_[RoverSettings::kLineBufferSize];
  size_t lineLen_ = 0;
};
