#include "quadrature_encoder.h"

#include <Arduino.h>

QuadratureEncoder *QuadratureEncoder::s_slots[2] = {nullptr, nullptr};

void QuadratureEncoder::begin(int pinA, int pinB, bool invert) {
  pinA_ = pinA;
  pinB_ = pinB;
  invert_ = invert;
  pinMode(pinA_, INPUT_PULLUP);
  pinMode(pinB_, INPUT_PULLUP);
  lastA_ = digitalRead(pinA_);
  lastB_ = digitalRead(pinB_);
  count_ = 0;
  delta_ = 0;

  for (int i = 0; i < 2; ++i) {
    if (s_slots[i] == nullptr) {
      slot_ = i;
      s_slots[i] = this;
      break;
    }
  }
  if (slot_ == 0) {
    attachInterrupt(digitalPinToInterrupt(pinA_), isrThunkA0, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pinB_), isrThunkB0, CHANGE);
  } else if (slot_ == 1) {
    attachInterrupt(digitalPinToInterrupt(pinA_), isrThunkA1, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pinB_), isrThunkB1, CHANGE);
  }
}

int32_t QuadratureEncoder::count() const {
  noInterrupts();
  const int32_t v = count_;
  interrupts();
  return v;
}

int32_t QuadratureEncoder::takeDelta() {
  noInterrupts();
  const int32_t d = delta_;
  delta_ = 0;
  interrupts();
  return d;
}

void QuadratureEncoder::reset() {
  noInterrupts();
  count_ = 0;
  delta_ = 0;
  interrupts();
}

void IRAM_ATTR QuadratureEncoder::onEdge(int /*pinChanged*/) {
  const int a = digitalRead(pinA_);
  const int b = digitalRead(pinB_);
  // Standard quadrature decode from previous state.
  const int prev = (lastA_ << 1) | lastB_;
  const int curr = (a << 1) | b;
  static const int8_t kTable[16] = {
    0, +1, -1, 0,
    -1, 0, 0, +1,
    +1, 0, 0, -1,
    0, -1, +1, 0,
  };
  int8_t step = kTable[(prev << 2) | curr];
  if (invert_) {
    step = static_cast<int8_t>(-step);
  }
  if (step != 0) {
    count_ += step;
    delta_ += step;
  }
  lastA_ = a;
  lastB_ = b;
}

void IRAM_ATTR QuadratureEncoder::isrThunkA0() {
  if (s_slots[0] != nullptr) {
    s_slots[0]->onEdge(s_slots[0]->pinA_);
  }
}

void IRAM_ATTR QuadratureEncoder::isrThunkB0() {
  if (s_slots[0] != nullptr) {
    s_slots[0]->onEdge(s_slots[0]->pinB_);
  }
}

void IRAM_ATTR QuadratureEncoder::isrThunkA1() {
  if (s_slots[1] != nullptr) {
    s_slots[1]->onEdge(s_slots[1]->pinA_);
  }
}

void IRAM_ATTR QuadratureEncoder::isrThunkB1() {
  if (s_slots[1] != nullptr) {
    s_slots[1]->onEdge(s_slots[1]->pinB_);
  }
}
