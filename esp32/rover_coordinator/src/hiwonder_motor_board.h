/**
 * I2C driver for the Hiwonder 4-channel encoder motor board.
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

class HiwonderMotorBoard {
 public:
  /** Configure Wire pins/clock and optional pull-ups. */
  void begin();

  /** Scan the I2C bus; return ACK count. Optionally print hits to Serial. */
  int scan(bool announce) const;

  /** Write motor type then polarity (blocks for settle). */
  bool initMotors(uint8_t motorType, uint8_t polarity);

  /** Closed-loop SPEED register (−limit..limit), with reverse coast. */
  bool setSpeed(int8_t m1, int8_t m2, int8_t m3, int8_t m4);

  /** Open-loop PWM register (−limit..limit), with reverse coast. */
  bool setPwm(int8_t m1, int8_t m2, int8_t m3, int8_t m4);

  /** Zero SPEED and PWM registers. */
  bool stop();

  /** Read battery millivolts from ADC_BAT. */
  bool readBatteryMv(uint16_t *outMv) const;

  /** Read four encoder totals into out[4]. */
  bool readEncoders(int32_t out[4]) const;

 private:
  bool writeBytes(uint8_t reg, const uint8_t *data, size_t len) const;
  bool readBytes(uint8_t reg, uint8_t *buf, size_t len) const;
  bool writeDrive(uint8_t reg, int8_t m1, int8_t m2, int8_t m3, int8_t m4);
  static bool signFlips(int8_t previous, int8_t next);
  bool coastIfReversing(int8_t m1, int8_t m2, int8_t m3, int8_t m4);

  int8_t lastM1_ = 0;
  int8_t lastM2_ = 0;
  int8_t lastM3_ = 0;
  int8_t lastM4_ = 0;
  uint8_t lastDriveReg_ = 0;
};
