/**
 * Waveshare onboard front drive: TB6612 Motor A/B + quadrature encoders + PID.
 * Protocol keeps 4 SPEED slots; M3/M4 are ignored (rear = other board later).
 */
#pragma once

#include <stdint.h>

#include "quadrature_encoder.h"
#include "tb6612_channel.h"
#include "wheel_velocity_pid.h"

class FrontDriveBoard {
 public:
  /** Configure pins, encoders, and PWM; start the 100 Hz control task. */
  void begin();

  /** Ready check (always true once begin() ran). */
  bool motorPresent() const;

  /** Announce readiness; returns 1 (front pair online). */
  int scan(bool announce) const;

  /** Reset encoders / PID state (motorType/polarity ignored, kept for protocol). */
  bool initMotors(uint8_t motorType, uint8_t polarity);

  /** Closed-loop SPEED (−limit..limit) for FL/FR; M3/M4 ignored. */
  bool setSpeed(int8_t m1, int8_t m2, int8_t m3, int8_t m4);

  /** Open-loop PWM (−limit..limit) mapped to duty; bypasses PID. */
  bool setPwm(int8_t m1, int8_t m2, int8_t m3, int8_t m4);

  /** Coast both channels and clear setpoints. */
  bool stop();

  /** Not available on this board — returns false. */
  bool readBatteryMv(uint16_t *outMv) const;

  /** Encoder totals: out[0]=FL, out[1]=FR, out[2]=0, out[3]=0. */
  bool readEncoders(int32_t out[4]) const;

 private:
  enum class Mode : uint8_t { Stopped, Speed, Pwm };

  static void driveTaskThunk(void *arg);
  void driveLoop();
  void applyCoastIfReversing(int8_t nextFl, int8_t nextFr);
  static float speedCmdToRpm(int8_t cmd);
  static int pwmCmdToDuty(int8_t cmd);
  static int signedDuty(int duty, bool invert);
  static int dutyFromPid(
    WheelVelocityPid &pid, float targetRpm, float measuredRpm, float dt);

  Tb6612Channel motorFl_;
  Tb6612Channel motorFr_;
  QuadratureEncoder encFl_;
  QuadratureEncoder encFr_;
  WheelVelocityPid pidFl_;
  WheelVelocityPid pidFr_;

  volatile Mode mode_ = Mode::Stopped;
  volatile int8_t cmdFl_ = 0;
  volatile int8_t cmdFr_ = 0;
  int8_t lastFl_ = 0;
  int8_t lastFr_ = 0;
  uint32_t brakeUntilMs_ = 0;
  bool started_ = false;
};
