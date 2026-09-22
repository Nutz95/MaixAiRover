#include "drive_failsafe.h"

#include <Arduino.h>

#include "coordinator_guard.h"
#include "coordinator_lock.h"
#include "front_drive_board.h"
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
  FrontDriveBoard &motors, ProtocolReply &reply, CoordinatorLock &lock) {
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
