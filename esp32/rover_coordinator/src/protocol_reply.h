/**
 * Fan-out OK/ERR replies to USB Serial and the WiFi TCP console.
 */
#pragma once

class ProtocolReply {
 public:
  /** Emit ``OK <msg>`` on Serial and WiFi console. */
  void ok(const char *msg) const;

  /** Emit ``ERR <msg>`` on Serial and WiFi console. */
  void err(const char *msg) const;

 private:
  void emit(const char *prefix, const char *msg) const;
};
