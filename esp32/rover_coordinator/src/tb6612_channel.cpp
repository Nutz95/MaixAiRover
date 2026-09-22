#include "tb6612_channel.h"

#include <Arduino.h>

#include "settings.h"

void Tb6612Channel::begin(int pwmPin, int in1Pin, int in2Pin, int ledcChannel) {
  pwmPin_ = pwmPin;
  in1Pin_ = in1Pin;
  in2Pin_ = in2Pin;
  channel_ = ledcChannel;
  pinMode(in1Pin_, OUTPUT);
  pinMode(in2Pin_, OUTPUT);
  digitalWrite(in1Pin_, LOW);
  digitalWrite(in2Pin_, LOW);
  ledcSetup(
    channel_,
    RoverSettings::kPwmLedcFreqHz,
    RoverSettings::kPwmLedcResolutionBits);
  ledcAttachPin(pwmPin_, channel_);
  ledcWrite(channel_, 0);
}

void Tb6612Channel::setDuty(int duty) {
  const int maxDuty = RoverSettings::kPwmMaxDuty;
  if (duty > maxDuty) {
    duty = maxDuty;
  } else if (duty < -maxDuty) {
    duty = -maxDuty;
  }
  if (duty == 0) {
    coast();
    return;
  }
  if (duty > 0) {
    digitalWrite(in1Pin_, HIGH);
    digitalWrite(in2Pin_, LOW);
    ledcWrite(channel_, static_cast<uint32_t>(duty));
  } else {
    digitalWrite(in1Pin_, LOW);
    digitalWrite(in2Pin_, HIGH);
    ledcWrite(channel_, static_cast<uint32_t>(-duty));
  }
}

void Tb6612Channel::brake() {
  digitalWrite(in1Pin_, HIGH);
  digitalWrite(in2Pin_, HIGH);
  ledcWrite(channel_, 0);
}

void Tb6612Channel::coast() {
  digitalWrite(in1Pin_, LOW);
  digitalWrite(in2Pin_, LOW);
  ledcWrite(channel_, 0);
}
