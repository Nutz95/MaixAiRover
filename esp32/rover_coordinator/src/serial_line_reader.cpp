#include "serial_line_reader.h"

#include "binary_command_handler.h"
#include "binary_protocol.h"
#include "command_dispatcher.h"
#include "protocol_reply.h"

void SerialLineReader::poll(
  Stream &stream,
  CommandDispatcher &dispatcher,
  BinaryCommandHandler &binary,
  ProtocolReply &reply) {
  while (stream.available() > 0) {
    if (binActive_) {
      if (!feedBinary(stream, binary)) {
        break;
      }
      continue;
    }

    const int next = stream.peek();
    if (next == BinaryProtocol::kSync) {
      stream.read();
      binActive_ = true;
      binLen_ = 0;
      continue;
    }

    const char c = static_cast<char>(stream.read());
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

bool SerialLineReader::feedBinary(Stream &stream, BinaryCommandHandler &binary) {
  while (stream.available() > 0) {
    binBuf_[binLen_++] = static_cast<uint8_t>(stream.read());
    if (binLen_ < 2) {
      continue;
    }
    const uint8_t type = binBuf_[0];
    const uint8_t len = binBuf_[1];
    if (len > BinaryProtocol::kMaxPayload) {
      binActive_ = false;
      binLen_ = 0;
      return true;
    }
    const size_t need = static_cast<size_t>(2 + len + 1);
    if (binLen_ < need) {
      continue;
    }
    const uint8_t crc = binBuf_[2 + len];
    const uint8_t expect = BinaryProtocol::crc8(binBuf_, static_cast<uint8_t>(2 + len));
    binActive_ = false;
    binLen_ = 0;
    if (crc == expect) {
      binary.handle(stream, type, binBuf_ + 2, len);
    }
    return true;
  }
  return false;
}
