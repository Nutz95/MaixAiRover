/**
 * Full-quadrature encoder counter (ISR on both channels).
 */
#pragma once

#include <Arduino.h>
#include <stdint.h>

class QuadratureEncoder {
 public:
  /**
   * Attach CHANGE interrupts on pinA/pinB.
   * ``invert`` flips the sign of counted edges.
   */
  void begin(int pinA, int pinB, bool invert = false);

  /** Cumulative edge count since begin/reset (signed). */
  int32_t count() const;

  /** Atomically read and clear the delta since the last take. */
  int32_t takeDelta();

  /** Reset cumulative and delta counters to zero. */
  void reset();

 private:
  static void IRAM_ATTR isrThunkA0();
  static void IRAM_ATTR isrThunkB0();
  static void IRAM_ATTR isrThunkA1();
  static void IRAM_ATTR isrThunkB1();
  void IRAM_ATTR onEdge(int pinChanged);

  int pinA_ = -1;
  int pinB_ = -1;
  bool invert_ = false;
  volatile int32_t count_ = 0;
  volatile int32_t delta_ = 0;
  volatile int lastA_ = 0;
  volatile int lastB_ = 0;
  int slot_ = -1;

  static QuadratureEncoder *s_slots[2];
};
