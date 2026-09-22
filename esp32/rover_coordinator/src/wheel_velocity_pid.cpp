#include "wheel_velocity_pid.h"

#include <math.h>

#include "settings.h"

void WheelVelocityPid::reset() {
  integral_ = 0.0f;
  lastError_ = 0.0f;
}

float WheelVelocityPid::update(float targetRpm, float measuredRpm, float dtSeconds) {
  if (dtSeconds <= 0.0f) {
    return 0.0f;
  }
  const float error = targetRpm - measuredRpm;
  const float maxDuty = static_cast<float>(RoverSettings::kPwmMaxDuty);
  // Tentative unsaturated output for anti-windup gate.
  const float provisional =
    RoverSettings::kPidKp * error +
    RoverSettings::kPidKi * integral_ +
    RoverSettings::kPidKd * ((error - lastError_) / dtSeconds);
  const bool saturating =
    (provisional > maxDuty && error > 0.0f) ||
    (provisional < -maxDuty && error < 0.0f);
  if (!saturating) {
    integral_ += error * dtSeconds;
    if (integral_ > RoverSettings::kPidIntegralLimit) {
      integral_ = RoverSettings::kPidIntegralLimit;
    } else if (integral_ < -RoverSettings::kPidIntegralLimit) {
      integral_ = -RoverSettings::kPidIntegralLimit;
    }
  }
  const float derivative = (error - lastError_) / dtSeconds;
  lastError_ = error;
  float out =
    RoverSettings::kPidKp * error +
    RoverSettings::kPidKi * integral_ +
    RoverSettings::kPidKd * derivative;
  if (out > maxDuty) {
    out = maxDuty;
  } else if (out < -maxDuty) {
    out = -maxDuty;
  }
  if (fabsf(targetRpm) < 0.5f) {
    integral_ = 0.0f;
    return 0.0f;
  }
  return out;
}
