/**
 * One TB6612 H-bridge channel (direction + PWM duty).
 */
#pragma once

#include <stdint.h>

class Tb6612Channel {
 public:
  /** Configure direction pins and LEDC PWM on ``pwmPin``. */
  void begin(int pwmPin, int in1Pin, int in2Pin, int ledcChannel);

  /** Apply signed duty (−max..+max). Zero coasts (both inputs low). */
  void setDuty(int duty);

  /** Short-brake both inputs high, PWM 0 (faster stop than coast). */
  void brake();

  /** Immediate coast (PWM 0, inputs low). */
  void coast();

 private:
  int pwmPin_ = -1;
  int in1Pin_ = -1;
  int in2Pin_ = -1;
  int channel_ = 0;
};
