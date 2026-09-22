#include "board_sensors.h"

#include <Arduino.h>
#include <Wire.h>
#include <string.h>

#include "settings.h"

namespace {

constexpr uint8_t kInaAddr = 0x42;
constexpr uint8_t kQmiAddrs[] = {0x6A, 0x6B};
constexpr uint8_t kAkAddr = 0x0C;

}  // namespace

void BoardSensors::begin() {
  pinMode(RoverSettings::kI2cSdaPin, INPUT_PULLUP);
  pinMode(RoverSettings::kI2cSclPin, INPUT_PULLUP);
  Wire.begin(RoverSettings::kI2cSdaPin, RoverSettings::kI2cSclPin);
  Wire.setClock(100000);
  Wire.setTimeOut(50);
  inaOk_ = probeIna();
  imuOk_ = probeImu();
  magOk_ = probeMag();
  Serial.printf(
    "sensors: INA219=%d QMI8658=%d@0x%02X AK09918=%d\n",
    inaOk_ ? 1 : 0,
    imuOk_ ? 1 : 0,
    static_cast<unsigned>(qmiAddr_),
    magOk_ ? 1 : 0);
}

void BoardSensors::readInto(BinaryProtocol::TelemPayload *out) const {
  memset(out, 0, sizeof(*out));
  if (inaOk_ && readIna(&out->busMv, &out->currentMa)) {
    out->flags = static_cast<uint8_t>(out->flags | BinaryProtocol::kFlagIna);
  }
  if (imuOk_ &&
      readImu(
        &out->axMg, &out->ayMg, &out->azMg,
        &out->gxCdps, &out->gyCdps, &out->gzCdps,
        &out->tempCentiC)) {
    out->flags = static_cast<uint8_t>(out->flags | BinaryProtocol::kFlagImu);
  }
  if (magOk_ && readMag(&out->mxDeciUt, &out->myDeciUt, &out->mzDeciUt)) {
    out->flags = static_cast<uint8_t>(out->flags | BinaryProtocol::kFlagMag);
  }
}

bool BoardSensors::writeReg(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool BoardSensors::readRegs(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  const size_t got = Wire.requestFrom(static_cast<int>(addr), static_cast<int>(len));
  if (got != len) {
    return false;
  }
  for (uint8_t i = 0; i < len; ++i) {
    buf[i] = static_cast<uint8_t>(Wire.read());
  }
  return true;
}

bool BoardSensors::probeIna() {
  uint8_t raw[2];
  return readRegs(kInaAddr, 0x00, raw, 2);
}

bool BoardSensors::probeImu() {
  for (uint8_t addr : kQmiAddrs) {
    uint8_t who = 0;
    if (!readRegs(addr, 0x00, &who, 1) || who != 0x05) {
      continue;
    }
    qmiAddr_ = addr;
    // Waveshare-style bring-up: disable → configure → enable aEN|gEN.
    writeReg(addr, 0x08, 0x00);  // CTRL7 off
    delay(10);
    writeReg(addr, 0x02, 0x60);  // CTRL1 ADDR_AI
    writeReg(addr, 0x03, 0x23);  // CTRL2 accel ±8g
    writeReg(addr, 0x04, 0x23);  // CTRL3 gyro
    writeReg(addr, 0x06, 0x00);  // CTRL5 LPF default
    writeReg(addr, 0x08, 0x03);  // CTRL7 aEN|gEN
    delay(50);
    uint8_t ctrl7 = 0;
    if (!readRegs(addr, 0x08, &ctrl7, 1) || (ctrl7 & 0x03) == 0) {
      Serial.printf("sensors: QMI@0x%02X CTRL7=0x%02X (enable failed)\n", addr, ctrl7);
      continue;
    }
    return true;
  }
  qmiAddr_ = 0;
  return false;
}

bool BoardSensors::probeMag() {
  uint8_t wia = 0;
  if (!readRegs(kAkAddr, 0x00, &wia, 1) || wia != 0x48) {
    return false;
  }
  writeReg(kAkAddr, 0x31, 0x02);  // continuous 10 Hz
  delay(10);
  return true;
}

bool BoardSensors::readIna(uint16_t *busMv, int16_t *currentMa) const {
  uint8_t busRaw[2];
  uint8_t shuntRaw[2];
  if (!readRegs(kInaAddr, 0x02, busRaw, 2)) {
    return false;
  }
  if (!readRegs(kInaAddr, 0x01, shuntRaw, 2)) {
    return false;
  }
  const uint16_t busReg = static_cast<uint16_t>((busRaw[0] << 8) | busRaw[1]);
  *busMv = static_cast<uint16_t>((busReg >> 3) * 4);
  const int16_t shunt = static_cast<int16_t>((shuntRaw[0] << 8) | shuntRaw[1]);
  *currentMa = static_cast<int16_t>((static_cast<int32_t>(shunt) * 10) / 10);
  return true;
}

bool BoardSensors::readImu(
  int16_t *ax, int16_t *ay, int16_t *az,
  int16_t *gx, int16_t *gy, int16_t *gz,
  int16_t *tempCentiC) const {
  if (qmiAddr_ == 0) {
    return false;
  }
  uint8_t raw[12];
  if (!readRegs(qmiAddr_, 0x35, raw, 12)) {
    return false;
  }
  auto s16 = [](uint8_t lo, uint8_t hi) -> int16_t {
    return static_cast<int16_t>(lo | (hi << 8));
  };
  *ax = s16(raw[0], raw[1]);
  *ay = s16(raw[2], raw[3]);
  *az = s16(raw[4], raw[5]);
  *gx = s16(raw[6], raw[7]);
  *gy = s16(raw[8], raw[9]);
  *gz = s16(raw[10], raw[11]);
  uint8_t traw[2];
  if (readRegs(qmiAddr_, 0x33, traw, 2)) {
    *tempCentiC = static_cast<int16_t>(s16(traw[0], traw[1]));
  } else {
    *tempCentiC = 0;
  }
  return true;
}

bool BoardSensors::readMag(int16_t *mx, int16_t *my, int16_t *mz) const {
  uint8_t st1 = 0;
  if (!readRegs(kAkAddr, 0x10, &st1, 1)) {
    return false;
  }
  if ((st1 & 0x01) == 0) {
    return false;
  }
  uint8_t raw[6];
  if (!readRegs(kAkAddr, 0x11, raw, 6)) {
    return false;
  }
  uint8_t st2 = 0;
  readRegs(kAkAddr, 0x18, &st2, 1);
  *mx = static_cast<int16_t>(raw[0] | (raw[1] << 8));
  *my = static_cast<int16_t>(raw[2] | (raw[3] << 8));
  *mz = static_cast<int16_t>(raw[4] | (raw[5] << 8));
  return true;
}
