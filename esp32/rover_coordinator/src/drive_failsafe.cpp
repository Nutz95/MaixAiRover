#include "drive_failsafe.h"

#include <Arduino.h>

#include "coordinator_lock.h"
#include "hiwonder_motor_board.h"
#include "protocol_reply.h"
#include "settings.h"

void DriveFailsafe::noteDriveActivity() {
  armed_ = true;
  lastDriveMs_ = millis();
}

void DriveFailsafe::clear() {
  armed_ = false;
}

void DriveFailsafe::poll(
  HiwonderMotorBoard &motors, ProtocolReply &reply, CoordinatorLock &lock) {
  if (!armed_) {
    return;
  }
  if ((millis() - lastDriveMs_) <= RoverSettings::kDriveTimeoutMs) {
    return;
  }
  CoordinatorGuard guard(lock);
  motors.stop();
  armed_ = false;
  reply.ok("TIMEOUT STOP");
}
