/**
 * Stops motors if no SPEED/PWM command arrives within the failsafe window.
 */
#pragma once

#include <stdint.h>

class HiwonderMotorBoard;
class ProtocolReply;

class DriveFailsafe {
 public:
  /** Mark that a non-zero drive command was accepted. */
  void noteDriveActivity();

  /** Clear activity (after explicit STOP). */
  void clear();

  /** If armed and timed out, stop motors and emit OK TIMEOUT STOP. */
  void poll(HiwonderMotorBoard &motors, ProtocolReply &reply);

 private:
  uint32_t lastDriveMs_ = 0;
  bool armed_ = false;
};
