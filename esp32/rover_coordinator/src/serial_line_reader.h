/**
 * Accumulate Stream bytes into text lines or binary frames.
 */
#pragma once

#include <Arduino.h>
#include <stddef.h>

#include "binary_protocol.h"
#include "settings.h"

class BinaryCommandHandler;
class CommandDispatcher;
class ProtocolReply;

class SerialLineReader {
 public:
  /**
   * Read available bytes; dispatch LF text lines or SYNC binary frames.
   */
  void poll(
    Stream &stream,
    CommandDispatcher &dispatcher,
    BinaryCommandHandler &binary,
    ProtocolReply &reply);

 private:
  bool feedBinary(Stream &stream, BinaryCommandHandler &binary);

  char lineBuf_[RoverSettings::kLineBufferSize];
  size_t lineLen_ = 0;

  uint8_t binBuf_[2 + BinaryProtocol::kMaxPayload + 1];
  size_t binLen_ = 0;
  bool binActive_ = false;
};
