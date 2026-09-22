/**
 * Compile-time settings for the Waveshare ESP32 rover coordinator.
 * Front wheels: onboard TB6612 + encoders. Maix link: UART0 (USB + aux P TX/RX).
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace RoverSettings {

// --- UART0: USB CP2102 (PC console / OTA debug) ---------------------------
constexpr uint32_t kUsbSerialBaud = 115200;
constexpr uint32_t kSerialBootDelayMs = 300;
constexpr size_t kLineBufferSize = 96;
constexpr size_t kReplyBufferSize = 128;

// --- Maix link: ESP32 UART2 on aux 10-pin header (not UART0 / not encoders)
// Maix TX → IO4 (ESP RX), Maix RX → IO5 (ESP TX), GND. IO27/IO16 = encoders.
constexpr int kMaixUartRxPin = 4;   // ESP receives (silk IO4)
constexpr int kMaixUartTxPin = 5;   // ESP transmits (silk IO5)
constexpr uint32_t kMaixUartBaud = 115200;

// --- Onboard TB6612 (Waveshare General Driver for Robots) -----------------
// Physical on this rover: Motor B connector = left (FL), Motor A = right (FR).
constexpr int kMotorAPwmPin = 25;
constexpr int kMotorAIn1Pin = 21;
constexpr int kMotorAIn2Pin = 17;
constexpr int kMotorBPwmPin = 26;
constexpr int kMotorBIn1Pin = 22;
constexpr int kMotorBIn2Pin = 23;

constexpr int kEncAPinA = 34;  // A_C1
constexpr int kEncAPinB = 35;  // A_C2
constexpr int kEncBPinA = 27;  // B_C1
constexpr int kEncBPinB = 16;  // B_C2

// Polarity: MA (right) spins opposite of firmware +duty → invert motor A.
// Encoder invert is independent (wrong enc sign → PID floors one wheel).
constexpr bool kInvertMotorA = true;
constexpr bool kInvertMotorB = false;
constexpr bool kInvertEncA = false;
constexpr bool kInvertEncB = true;  // FL counts negative on +PWM without this

constexpr int kPwmLedcChannelA = 0;
constexpr int kPwmLedcChannelB = 1;
constexpr int kPwmLedcFreqHz = 20000;
constexpr int kPwmLedcResolutionBits = 10;  // 0..1023
constexpr int kPwmMaxDuty = (1 << kPwmLedcResolutionBits) - 1;

// Motor mechanical model (JGB-style mecanum fronts).
constexpr int kEncoderPpr = 11;           // pulses per motor rev (one channel)
constexpr int kEncoderQuadrature = 4;     // full edges A/B
constexpr int kGearRatio = 56;
constexpr float kMaxWheelRpm = 178.0f;
constexpr int kCountsPerMotorRev = kEncoderPpr * kEncoderQuadrature;  // 44
constexpr int kCountsPerWheelRev = kCountsPerMotorRev * kGearRatio;   // 2464

// Closed-loop SPEED command range (protocol, same as before).
constexpr int kSpeedLimit = 50;
constexpr int kPwmLimit = 100;

// Velocity PID (RPM space), 100 Hz + duty feed-forward.
// Ki was too aggressive at no-load (one wheel coasted while the other ran away
// when encoder sign/magnitude disagreed). FF carries most of the duty; PID trims.
constexpr uint32_t kDriveControlPeriodMs = 10;
constexpr float kPidKp = 2.5f;
constexpr float kPidKi = 1.5f;
constexpr float kPidKd = 0.02f;
constexpr float kPidIntegralLimit = 120.0f;
constexpr uint32_t kStopBrakeMs = 25;

// Coast at 0 before applying a sign flip (protects H-bridge FETs).
// Kept short / non-blocking in applyCoastIfReversing (no delay() on cmd task).
constexpr uint32_t kMotorReverseCoastMs = 0;

// --- Drive failsafe -------------------------------------------------------
constexpr uint32_t kDriveTimeoutMs = 1500;

// --- FreeRTOS task sizing -------------------------------------------------
constexpr uint32_t kWifiTaskStack = 6144;
constexpr uint32_t kCommandTaskStack = 6144;
constexpr uint32_t kDriveTaskStack = 4096;
constexpr uint32_t kWifiTaskPriority = 1;
constexpr uint32_t kCommandTaskPriority = 2;
constexpr uint32_t kDriveTaskPriority = 3;
constexpr int kWifiTaskCore = 0;
constexpr int kCommandTaskCore = 1;
constexpr int kDriveTaskCore = 1;
constexpr uint32_t kCommandTaskPeriodMs = 5;
constexpr uint32_t kWifiTaskPeriodMs = 20;

// --- WiFi / OTA / TCP console ---------------------------------------------
#ifndef ARDUINO_OTA_HOSTNAME
#define ARDUINO_OTA_HOSTNAME "maixairover-front"
#endif
constexpr uint16_t kWifiConsolePort = 2333;
constexpr uint32_t kWifiOfflineLogIntervalMs = 10000;

// Onboard IMU/mag (I2C still available; not required for front drive).
constexpr int kI2cSdaPin = 32;
constexpr int kI2cSclPin = 33;
constexpr uint8_t kAk09918I2cAddress = 0x0C;
constexpr uint8_t kQmi8658I2cAddress = 0x6A;

}  // namespace RoverSettings
