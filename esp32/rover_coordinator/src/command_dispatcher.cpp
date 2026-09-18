#include "command_dispatcher.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "coordinator_lock.h"
#include "drive_failsafe.h"
#include "hiwonder_motor_board.h"
#include "protocol_reply.h"
#include "settings.h"
#include "wifi_runtime.h"

CommandDispatcher *CommandDispatcher::s_instance = nullptr;

CommandDispatcher::CommandDispatcher(
  HiwonderMotorBoard &motors,
  DriveFailsafe &failsafe,
  ProtocolReply &reply,
  WifiRuntime &wifi,
  CoordinatorLock &lock)
  : motors_(motors),
    failsafe_(failsafe),
    reply_(reply),
    wifi_(wifi),
    lock_(lock) {}

void CommandDispatcher::bindWifiThunk() {
  s_instance = this;
}

void CommandDispatcher::wifiThunk(char *line) {
  if (s_instance != nullptr) {
    s_instance->handleLine(line);
  }
}

int8_t CommandDispatcher::clampI8(long value, int lo, int hi) {
  if (value < lo) {
    return static_cast<int8_t>(lo);
  }
  if (value > hi) {
    return static_cast<int8_t>(hi);
  }
  return static_cast<int8_t>(value);
}

void CommandDispatcher::handleLine(char *line) {
  CoordinatorGuard guard(lock_);
  while (*line == ' ' || *line == '\t') {
    ++line;
  }
  if (*line == '\0') {
    return;
  }

  if (strcmp(line, "PING") == 0) {
    reply_.ok("PONG");
    return;
  }
  if (strcmp(line, "WIFI") == 0) {
    handleWifi();
    return;
  }
  if (strcmp(line, "SCAN") == 0) {
    handleScan();
    return;
  }
  if (strncmp(line, "INIT", 4) == 0) {
    handleInit(line);
    return;
  }
  if (strcmp(line, "STOP") == 0) {
    if (!motors_.stop()) {
      reply_.err("STOP");
      return;
    }
    failsafe_.clear();
    reply_.ok("STOP");
    return;
  }
  if (strncmp(line, "SPEED", 5) == 0) {
    handleDrive(line, false);
    return;
  }
  if (strncmp(line, "PWM", 3) == 0) {
    handleDrive(line, true);
    return;
  }
  if (strcmp(line, "BAT") == 0) {
    handleBattery();
    return;
  }
  if (strcmp(line, "ENC") == 0) {
    handleEncoders();
    return;
  }
  reply_.err("unknown");
}

void CommandDispatcher::handleInit(char *line) {
  long type = RoverSettings::kDefaultMotorTypeJgb;
  long pol = RoverSettings::kDefaultEncoderPolarity;
  sscanf(line + 4, "%ld %ld", &type, &pol);
  if (!motors_.initMotors(static_cast<uint8_t>(type), static_cast<uint8_t>(pol))) {
    reply_.err("INIT");
    return;
  }
  reply_.ok("INIT");
}

void CommandDispatcher::handleDrive(char *line, bool pwm) {
  long a = 0;
  long b = 0;
  long c = 0;
  long d = 0;
  const char *args = pwm ? line + 3 : line + 5;
  if (sscanf(args, "%ld %ld %ld %ld", &a, &b, &c, &d) != 4) {
    reply_.err(pwm ? "PWM args" : "SPEED args");
    return;
  }
  const int lim = pwm ? RoverSettings::kPwmLimit : RoverSettings::kSpeedLimit;
  const int8_t m1 = clampI8(a, -lim, lim);
  const int8_t m2 = clampI8(b, -lim, lim);
  const int8_t m3 = clampI8(c, -lim, lim);
  const int8_t m4 = clampI8(d, -lim, lim);
  const bool ok = pwm ? motors_.setPwm(m1, m2, m3, m4) : motors_.setSpeed(m1, m2, m3, m4);
  if (!ok) {
    reply_.err(pwm ? "PWM i2c" : "SPEED i2c");
    return;
  }
  if ((m1 | m2 | m3 | m4) != 0) {
    failsafe_.noteDriveActivity();
  } else {
    failsafe_.clear();
  }
  char msg[48];
  snprintf(
    msg,
    sizeof(msg),
    "%s %d %d %d %d",
    pwm ? "PWM" : "SPEED",
    static_cast<int>(m1),
    static_cast<int>(m2),
    static_cast<int>(m3),
    static_cast<int>(m4));
  reply_.ok(msg);
}

void CommandDispatcher::handleBattery() {
  uint16_t mv = 0;
  if (!motors_.readBatteryMv(&mv)) {
    reply_.err("BAT");
    return;
  }
  char msg[32];
  snprintf(msg, sizeof(msg), "BAT %u", static_cast<unsigned>(mv));
  reply_.ok(msg);
}

void CommandDispatcher::handleEncoders() {
  int32_t enc[4];
  if (!motors_.readEncoders(enc)) {
    reply_.err("ENC");
    return;
  }
  char msg[80];
  snprintf(
    msg,
    sizeof(msg),
    "ENC %ld %ld %ld %ld",
    static_cast<long>(enc[0]),
    static_cast<long>(enc[1]),
    static_cast<long>(enc[2]),
    static_cast<long>(enc[3]));
  reply_.ok(msg);
}

void CommandDispatcher::handleWifi() {
  char ip[32];
  if (!wifi_.localIp(ip, sizeof(ip))) {
    reply_.err("WIFI down");
    return;
  }
  char msg[64];
  snprintf(
    msg,
    sizeof(msg),
    "WIFI %s console=:%u",
    ip,
    static_cast<unsigned>(RoverSettings::kWifiConsolePort));
  reply_.ok(msg);
}

void CommandDispatcher::handleScan() {
  const int n = motors_.scan(true);
  char msg[32];
  snprintf(msg, sizeof(msg), "SCAN %d", n);
  if (n > 0) {
    reply_.ok(msg);
  } else {
    reply_.err(msg);
  }
}
