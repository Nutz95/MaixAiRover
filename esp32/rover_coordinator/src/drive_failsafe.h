/**
 * Stops motors if no SPEED/PWM command arrives within the failsafe window.
 */
#pragma once

#include <stdint.h>

class CoordinatorLock;
class FrontDriveBoard;
class ProtocolReply;

class DriveFailsafe {
 public:
  /** Mark that a non-zero drive command was accepted. */
  void noteDriveActivity();

  /** Clear activity (after explicit STOP). */
  void clear();

  /** If armed and timed out, stop motors and emit OK TIMEOUT STOP. */
  void poll(FrontDriveBoard &motors, ProtocolReply &reply, CoordinatorLock &lock);

 private:
  uint32_t lastDriveMs_ = 0;
  bool armed_ = false;
};
