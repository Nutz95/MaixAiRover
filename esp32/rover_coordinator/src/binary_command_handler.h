/**
 * Handle binary command frames and emit binary replies on a Stream.
 */
#pragma once

#include <stdint.h>

#include <Arduino.h>

class BoardSensors;
class CoordinatorLock;
class DriveFailsafe;
class FrontDriveBoard;

class BinaryCommandHandler {
 public:
  BinaryCommandHandler(
    FrontDriveBoard &motors,
    DriveFailsafe &failsafe,
    BoardSensors &sensors,
    CoordinatorLock &lock);

  /** Parse one complete frame (TYPE..CRC already validated) and reply. */
  void handle(Stream &out, uint8_t type, const uint8_t *payload, uint8_t len);

 private:
  void sendFrame(Stream &out, uint8_t type, const uint8_t *payload, uint8_t len);
  void sendAck(Stream &out, uint8_t reqType);
  void sendErr(Stream &out, uint8_t code);
  void handleTelem(Stream &out);

  FrontDriveBoard &motors_;
  DriveFailsafe &failsafe_;
  BoardSensors &sensors_;
  CoordinatorLock &lock_;
};
