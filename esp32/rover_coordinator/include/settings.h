/**
 * Compile-time settings for the Waveshare ESP32 rover coordinator.
 * Keep magic numbers out of .cpp files.
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace RoverSettings {

// --- USB Serial (flash / PC smoke) — ESP32 UART0 ---------------------------
constexpr uint32_t kUsbSerialBaud = 115200;
constexpr uint32_t kSerialBootDelayMs = 300;
constexpr size_t kLineBufferSize = 96;
constexpr size_t kReplyBufferSize = 128;

// --- MaixCAM UART (HardwareSerial UART2 on free Dupont pins) --------------
// Silkscreen "RX" on the middle header is UART0 RX (GPIO3), shared with the
// USB CP2102 — do NOT use it for the camera link while debugging over USB.
// Use free header pins IO14/IO15 instead (see docs/wiring.md).
constexpr int kCamUartRxPin = 15;  // Dupont IO15 — ESP RX <- Maix TX
constexpr int kCamUartTxPin = 14;  // Dupont IO14 — ESP TX -> Maix RX
constexpr uint32_t kCamUartBaud = 115200;
constexpr int kCamUartNum = 2;     // UART2

// --- I2C (Waveshare IIC expansion -> Hiwonder + onboard IMU/mag) -----------
constexpr int kI2cSdaPin = 32;
constexpr int kI2cSclPin = 33;
constexpr uint32_t kI2cClockHz = 100000;
constexpr uint16_t kI2cTimeoutMs = 50;
constexpr uint8_t kI2cScanAddrMin = 0x08;
constexpr uint8_t kI2cScanAddrMax = 0x77;

// Onboard AK09918C magnetometer (via 1.8V bus + TXS0104 level shifter).
constexpr uint8_t kAk09918I2cAddress = 0x0C;
// Onboard QMI8658C 6-axis IMU (same I2C bus).
constexpr uint8_t kQmi8658I2cAddress = 0x6A;

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

// Coast at 0 before applying a sign flip (protects H-bridge / motor FETs).
constexpr uint32_t kMotorReverseCoastMs = 80;

// --- Drive failsafe -------------------------------------------------------
constexpr uint32_t kDriveTimeoutMs = 1500;

// --- FreeRTOS task sizing -------------------------------------------------
constexpr uint32_t kWifiTaskStack = 6144;
constexpr uint32_t kCommandTaskStack = 6144;
constexpr uint32_t kWifiTaskPriority = 1;
constexpr uint32_t kCommandTaskPriority = 2;
constexpr int kWifiTaskCore = 0;
constexpr int kCommandTaskCore = 1;
constexpr uint32_t kCommandTaskPeriodMs = 5;
constexpr uint32_t kWifiTaskPeriodMs = 20;

// --- WiFi / OTA / TCP console ---------------------------------------------
#ifndef ARDUINO_OTA_HOSTNAME
#define ARDUINO_OTA_HOSTNAME "maixairover-esp"
#endif
constexpr uint16_t kWifiConsolePort = 2333;
constexpr uint32_t kWifiOfflineLogIntervalMs = 10000;

}  // namespace RoverSettings
