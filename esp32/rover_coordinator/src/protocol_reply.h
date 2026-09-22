/**
 * Fan-out OK/ERR replies to the active command Stream + WiFi TCP console.
 *
 * USB Serial (UART0) stays for PC/debug. Maix link uses Serial2 (IO4/IO5);
 * setOut() routes text replies to whichever port just received a command.
 */
#pragma once

#include <Arduino.h>

class ProtocolReply {
 public:
  /** Route subsequent OK/ERR lines to this stream (USB or Maix UART). */
  void setOut(Stream &out);

  /** Emit ``OK <msg>`` on the active stream and WiFi console. */
  void ok(const char *msg) const;

  /** Emit ``ERR <msg>`` on the active stream and WiFi console. */
  void err(const char *msg) const;

 private:
  void emit(const char *prefix, const char *msg) const;

  Stream *out_ = &Serial;
};
