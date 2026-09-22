/**
 * Onboard Waveshare sensors: INA219 power + QMI8658 IMU + AK09918 mag.
 */
#pragma once

#include <stdint.h>

#include "binary_protocol.h"

class BoardSensors {
 public:
  /** Init I2C bus and probe/configure sensors (best-effort). */
  void begin();

  /** Fill a telemetry payload (encoders filled by caller). */
  void readInto(BinaryProtocol::TelemPayload *out) const;

 private:
  bool inaOk_ = false;
  bool imuOk_ = false;
  bool magOk_ = false;
  uint8_t qmiAddr_ = 0;

  bool probeIna();
  bool probeImu();
  bool probeMag();
  bool readIna(uint16_t *busMv, int16_t *currentMa) const;
  bool readImu(
    int16_t *ax, int16_t *ay, int16_t *az,
    int16_t *gx, int16_t *gy, int16_t *gz,
    int16_t *tempCentiC) const;
  bool readMag(int16_t *mx, int16_t *my, int16_t *mz) const;
  static bool writeReg(uint8_t addr, uint8_t reg, uint8_t value);
  static bool readRegs(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len);
};
