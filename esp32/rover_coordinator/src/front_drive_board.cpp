#include "front_drive_board.h"

#include <Arduino.h>
#include <math.h>

#include "settings.h"

void FrontDriveBoard::begin() {
  // FL ← Motor B (left), FR ← Motor A (right) — matches physical connectors.
  motorFl_.begin(
    RoverSettings::kMotorBPwmPin,
    RoverSettings::kMotorBIn1Pin,
    RoverSettings::kMotorBIn2Pin,
    RoverSettings::kPwmLedcChannelB);
  motorFr_.begin(
    RoverSettings::kMotorAPwmPin,
    RoverSettings::kMotorAIn1Pin,
    RoverSettings::kMotorAIn2Pin,
    RoverSettings::kPwmLedcChannelA);
  encFl_.begin(
    RoverSettings::kEncBPinA,
    RoverSettings::kEncBPinB,
    RoverSettings::kInvertEncB);
  encFr_.begin(
    RoverSettings::kEncAPinA,
    RoverSettings::kEncAPinB,
    RoverSettings::kInvertEncA);
  pidFl_.reset();
  pidFr_.reset();
  stop();
  if (!started_) {
    started_ = true;
    xTaskCreatePinnedToCore(
      driveTaskThunk,
      "drive",
      RoverSettings::kDriveTaskStack,
      this,
      RoverSettings::kDriveTaskPriority,
      nullptr,
      RoverSettings::kDriveTaskCore);
  }
}

bool FrontDriveBoard::motorPresent() const {
  return started_;
}

int FrontDriveBoard::scan(bool announce) const {
  if (announce) {
    Serial.println("drive: onboard TB6612 front FL/FR (encoders A/B)");
  }
  return started_ ? 1 : 0;
}

bool FrontDriveBoard::initMotors(uint8_t /*motorType*/, uint8_t /*polarity*/) {
  encFl_.reset();
  encFr_.reset();
  pidFl_.reset();
  pidFr_.reset();
  return stop();
}

bool FrontDriveBoard::setSpeed(int8_t m1, int8_t m2, int8_t /*m3*/, int8_t /*m4*/) {
  applyCoastIfReversing(m1, m2);
  cmdFl_ = m1;
  cmdFr_ = m2;
  lastFl_ = m1;
  lastFr_ = m2;
  if (m1 == 0 && m2 == 0) {
    return stop();
  }
  brakeUntilMs_ = 0;
  mode_ = Mode::Speed;
  return true;
}

bool FrontDriveBoard::setPwm(int8_t m1, int8_t m2, int8_t /*m3*/, int8_t /*m4*/) {
  applyCoastIfReversing(m1, m2);
  cmdFl_ = m1;
  cmdFr_ = m2;
  lastFl_ = m1;
  lastFr_ = m2;
  if (m1 == 0 && m2 == 0) {
    return stop();
  }
  mode_ = Mode::Pwm;
  motorFl_.setDuty(signedDuty(pwmCmdToDuty(m1), RoverSettings::kInvertMotorB));
  motorFr_.setDuty(signedDuty(pwmCmdToDuty(m2), RoverSettings::kInvertMotorA));
  return true;
}

bool FrontDriveBoard::stop() {
  cmdFl_ = 0;
  cmdFr_ = 0;
  lastFl_ = 0;
  lastFr_ = 0;
  mode_ = Mode::Stopped;
  pidFl_.reset();
  pidFr_.reset();
  motorFl_.brake();
  motorFr_.brake();
  // Non-blocking: command task must not delay(UART). Drive loop coasts later.
  brakeUntilMs_ = millis() + RoverSettings::kStopBrakeMs;
  return true;
}

bool FrontDriveBoard::readBatteryMv(uint16_t * /*outMv*/) const {
  return false;
}

bool FrontDriveBoard::readEncoders(int32_t out[4]) const {
  out[0] = encFl_.count();
  out[1] = encFr_.count();
  out[2] = 0;
  out[3] = 0;
  return true;
}

void FrontDriveBoard::driveTaskThunk(void *arg) {
  static_cast<FrontDriveBoard *>(arg)->driveLoop();
}

void FrontDriveBoard::driveLoop() {
  const float dt =
    static_cast<float>(RoverSettings::kDriveControlPeriodMs) / 1000.0f;
  const float countsPerWheel =
    static_cast<float>(RoverSettings::kCountsPerWheelRev);
  for (;;) {
    const Mode mode = mode_;
    if (mode == Mode::Speed) {
      const int8_t cmdFl = cmdFl_;
      const int8_t cmdFr = cmdFr_;
      const int32_t dFl = encFl_.takeDelta();
      const int32_t dFr = encFr_.takeDelta();
      const float rpmFl = (static_cast<float>(dFl) / countsPerWheel) * (60.0f / dt);
      const float rpmFr = (static_cast<float>(dFr) / countsPerWheel) * (60.0f / dt);
      const float tgtFl = speedCmdToRpm(cmdFl);
      const float tgtFr = speedCmdToRpm(cmdFr);
      motorFl_.setDuty(signedDuty(
        dutyFromPid(pidFl_, tgtFl, rpmFl, dt),
        RoverSettings::kInvertMotorB));
      motorFr_.setDuty(signedDuty(
        dutyFromPid(pidFr_, tgtFr, rpmFr, dt),
        RoverSettings::kInvertMotorA));
    } else if (mode == Mode::Stopped) {
      const int32_t dFl = encFl_.takeDelta();
      const int32_t dFr = encFr_.takeDelta();
      // Hold brake until both wheels are nearly still (right was freewheeling).
      if (abs(dFl) > 2 || abs(dFr) > 2) {
        motorFl_.brake();
        motorFr_.brake();
        brakeUntilMs_ = millis() + RoverSettings::kStopBrakeMs;
      } else if (brakeUntilMs_ != 0 &&
                 static_cast<int32_t>(millis() - brakeUntilMs_) >= 0) {
        motorFl_.coast();
        motorFr_.coast();
        brakeUntilMs_ = 0;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(RoverSettings::kDriveControlPeriodMs));
  }
}

void FrontDriveBoard::applyCoastIfReversing(int8_t nextFl, int8_t nextFr) {
  const bool flipFl = lastFl_ != 0 && nextFl != 0 && ((lastFl_ > 0) != (nextFl > 0));
  const bool flipFr = lastFr_ != 0 && nextFr != 0 && ((lastFr_ > 0) != (nextFr > 0));
  if (!flipFl && !flipFr) {
    return;
  }
  motorFl_.coast();
  motorFr_.coast();
  pidFl_.reset();
  pidFr_.reset();
  // ponytail: no delay() here — blocked the UART cmd task (~80ms) and felt like
  // stick lag. Drive loop re-applies within 10ms; TB6612 tolerates quick reverse
  // at our duty levels. Restore a timed coast in the drive task if FETs complain.
}

float FrontDriveBoard::speedCmdToRpm(int8_t cmd) {
  const float lim = static_cast<float>(RoverSettings::kSpeedLimit);
  if (lim <= 0.0f) {
    return 0.0f;
  }
  return (static_cast<float>(cmd) / lim) * RoverSettings::kMaxWheelRpm;
}

int FrontDriveBoard::pwmCmdToDuty(int8_t cmd) {
  const float lim = static_cast<float>(RoverSettings::kPwmLimit);
  if (lim <= 0.0f) {
    return 0;
  }
  return static_cast<int>(
    lroundf((static_cast<float>(cmd) / lim) * static_cast<float>(RoverSettings::kPwmMaxDuty)));
}

int FrontDriveBoard::signedDuty(int duty, bool invert) {
  return invert ? -duty : duty;
}

int FrontDriveBoard::dutyFromPid(
  WheelVelocityPid &pid, float targetRpm, float measuredRpm, float dt) {
  if (fabsf(targetRpm) < 0.5f) {
    pid.reset();
    return 0;
  }
  const float maxDuty = static_cast<float>(RoverSettings::kPwmMaxDuty);
  const float ff =
    (targetRpm / RoverSettings::kMaxWheelRpm) * maxDuty;
  const float trim = pid.update(targetRpm, measuredRpm, dt);
  return static_cast<int>(lroundf(ff + trim));
}
