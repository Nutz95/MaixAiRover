#include "hiwonder_motor_board.h"

#include <Arduino.h>
#include <Wire.h>

#include "settings.h"

void HiwonderMotorBoard::begin() {
  pinMode(RoverSettings::kI2cSdaPin, INPUT_PULLUP);
  pinMode(RoverSettings::kI2cSclPin, INPUT_PULLUP);
  Wire.begin(RoverSettings::kI2cSdaPin, RoverSettings::kI2cSclPin);
  Wire.setClock(RoverSettings::kI2cClockHz);
  Wire.setTimeOut(RoverSettings::kI2cTimeoutMs);
}

bool HiwonderMotorBoard::writeBytes(uint8_t reg, const uint8_t *data, size_t len) const {
  Wire.beginTransmission(RoverSettings::kMotorI2cAddress);
  Wire.write(reg);
  for (size_t i = 0; i < len; ++i) {
    Wire.write(data[i]);
  }
  return Wire.endTransmission() == 0;
}

bool HiwonderMotorBoard::readBytes(uint8_t reg, uint8_t *buf, size_t len) const {
  Wire.beginTransmission(RoverSettings::kMotorI2cAddress);
  Wire.write(reg);
  if (Wire.endTransmission(true) != 0) {
    return false;
  }
  size_t got = Wire.requestFrom(
    static_cast<int>(RoverSettings::kMotorI2cAddress),
    static_cast<int>(len));
  if (got != len) {
    return false;
  }
  for (size_t i = 0; i < len; ++i) {
    buf[i] = Wire.read();
  }
  return true;
}

bool HiwonderMotorBoard::writeDrive(
  uint8_t reg, int8_t m1, int8_t m2, int8_t m3, int8_t m4) const {
  const uint8_t payload[4] = {
    static_cast<uint8_t>(m1),
    static_cast<uint8_t>(m2),
    static_cast<uint8_t>(m3),
    static_cast<uint8_t>(m4),
  };
  return writeBytes(reg, payload, 4);
}

int HiwonderMotorBoard::scan(bool announce) const {
  int found = 0;
  bool sawMotor = false;
  if (announce) {
    Serial.println("I2C scan...");
  }
  for (uint8_t addr = RoverSettings::kI2cScanAddrMin;
       addr <= RoverSettings::kI2cScanAddrMax;
       ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  ACK 0x%02X", addr);
      if (addr == RoverSettings::kMotorI2cAddress) {
        Serial.print(" <- Hiwonder");
        sawMotor = true;
      }
      Serial.println();
      found++;
    }
  }
  if (announce) {
    Serial.printf(
      "  %d device(s)%s\n",
      found,
      sawMotor ? "" : " - 0x34 MISSING");
  }
  return found;
}

bool HiwonderMotorBoard::initMotors(uint8_t motorType, uint8_t polarity) const {
  if (!writeBytes(RoverSettings::kRegMotorType, &motorType, 1)) {
    return false;
  }
  delay(RoverSettings::kMotorInitSettleMs);
  const uint8_t pol = polarity ? 1 : 0;
  return writeBytes(RoverSettings::kRegEncoderPolarity, &pol, 1);
}

bool HiwonderMotorBoard::setSpeed(int8_t m1, int8_t m2, int8_t m3, int8_t m4) const {
  return writeDrive(RoverSettings::kRegFixedSpeed, m1, m2, m3, m4);
}

bool HiwonderMotorBoard::setPwm(int8_t m1, int8_t m2, int8_t m3, int8_t m4) const {
  return writeDrive(RoverSettings::kRegFixedPwm, m1, m2, m3, m4);
}

bool HiwonderMotorBoard::stop() const {
  const uint8_t z[4] = {0, 0, 0, 0};
  const bool ok = writeBytes(RoverSettings::kRegFixedSpeed, z, 4);
  writeBytes(RoverSettings::kRegFixedPwm, z, 4);
  return ok;
}

bool HiwonderMotorBoard::readBatteryMv(uint16_t *outMv) const {
  uint8_t raw[2];
  if (!readBytes(RoverSettings::kRegAdcBat, raw, 2)) {
    return false;
  }
  *outMv = static_cast<uint16_t>(raw[0] | (raw[1] << 8));
  return true;
}

bool HiwonderMotorBoard::readEncoders(int32_t out[4]) const {
  uint8_t raw[16];
  if (!readBytes(RoverSettings::kRegEncoderTotal, raw, 16)) {
    return false;
  }
  for (int i = 0; i < 4; ++i) {
    out[i] = static_cast<int32_t>(
      static_cast<uint32_t>(raw[i * 4]) |
      (static_cast<uint32_t>(raw[i * 4 + 1]) << 8) |
      (static_cast<uint32_t>(raw[i * 4 + 2]) << 16) |
      (static_cast<uint32_t>(raw[i * 4 + 3]) << 24));
  }
  return true;
}
