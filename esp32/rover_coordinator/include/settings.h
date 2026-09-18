/**
 * Compile-time settings for the Waveshare ESP32 rover coordinator.
 * Keep magic numbers out of .cpp files.
 */
#pragma once

#include <stdint.h>

namespace RoverSettings {

// --- UART (USB / MaixCAM) -------------------------------------------------
constexpr uint32_t kSerialBaud = 115200;
constexpr uint32_t kSerialBootDelayMs = 300;
constexpr size_t kLineBufferSize = 96;
constexpr size_t kReplyBufferSize = 128;

// --- I2C (Waveshare IIC expansion -> Hiwonder) -----------------------------
constexpr int kI2cSdaPin = 32;
constexpr int kI2cSclPin = 33;
constexpr uint32_t kI2cClockHz = 100000;
constexpr uint16_t kI2cTimeoutMs = 50;
constexpr uint8_t kI2cScanAddrMin = 0x08;
constexpr uint8_t kI2cScanAddrMax = 0x77;

// --- Hiwonder motor board -------------------------------------------------
constexpr uint8_t kMotorI2cAddress = 0x34;
constexpr uint8_t kRegAdcBat = 0x00;
constexpr uint8_t kRegMotorType = 0x14;
constexpr uint8_t kRegEncoderPolarity = 0x15;
constexpr uint8_t kRegFixedPwm = 0x1F;
constexpr uint8_t kRegFixedSpeed = 0x33;
constexpr uint8_t kRegEncoderTotal = 0x3C;

constexpr uint8_t kDefaultMotorTypeJgb = 3;
constexpr uint8_t kDefaultEncoderPolarity = 0;
constexpr uint32_t kMotorInitSettleMs = 500;

constexpr int kSpeedLimit = 50;
constexpr int kPwmLimit = 100;

// --- Drive failsafe -------------------------------------------------------
constexpr uint32_t kDriveTimeoutMs = 1500;

// --- WiFi / OTA / TCP console ---------------------------------------------
#ifndef ARDUINO_OTA_HOSTNAME
#define ARDUINO_OTA_HOSTNAME "maixairover-esp"
#endif
constexpr uint16_t kWifiConsolePort = 2333;
constexpr uint32_t kWifiOfflineLogIntervalMs = 10000;

}  // namespace RoverSettings
