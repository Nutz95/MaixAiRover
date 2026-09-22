/**
 * Parse UART/TCP line protocol and dispatch to motor / wifi / sensors.
 */
#pragma once

#include <stdint.h>

class BoardSensors;
class DriveFailsafe;
class FrontDriveBoard;
class ProtocolReply;
class WifiRuntime;
class CoordinatorLock;

class CommandDispatcher {
 public:
  CommandDispatcher(
    FrontDriveBoard &motors,
    DriveFailsafe &failsafe,
    ProtocolReply &reply,
    WifiRuntime &wifi,
    CoordinatorLock &lock,
    BoardSensors &sensors);

  /** Handle one NUL-terminated command line (mutates whitespace in place). */
  void handleLine(char *line);

  /**
   * C thunk for WifiConsole::LineHandler.
   * Call bindWifiThunk() once before WifiConsole::setLineHandler.
   */
  static void wifiThunk(char *line);
  void bindWifiThunk();

 private:
  static int8_t clampI8(long value, int lo, int hi);
  void handleInit(char *line);
  void handleDrive(char *line, bool pwm);
  void handleBattery();
  void handleEncoders();
  void handleWifi();
  void handleScan();

  FrontDriveBoard &motors_;
  DriveFailsafe &failsafe_;
  ProtocolReply &reply_;
  WifiRuntime &wifi_;
  CoordinatorLock &lock_;
  BoardSensors &sensors_;
  static CommandDispatcher *s_instance;
};
