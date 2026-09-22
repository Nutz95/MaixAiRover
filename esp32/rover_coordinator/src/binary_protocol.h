/**
 * Binary framing for Maix↔ESP (compact command + telemetry).
 * Text line protocol remains for human Serial/WiFi console.
 *
 * Frame: SYNC(0xA5) TYPE LEN PAYLOAD[LEN] CRC8
 * CRC8 = sum(TYPE..PAYLOAD) & 0xFF
 */
#pragma once

#include <stdint.h>

namespace BinaryProtocol {

constexpr uint8_t kSync = 0xA5;
constexpr uint8_t kMaxPayload = 64;

constexpr uint8_t kCmdPing = 0x01;
constexpr uint8_t kCmdStop = 0x02;
constexpr uint8_t kCmdSpeed = 0x03;   // 4×int8
constexpr uint8_t kCmdPwm = 0x04;     // 4×int8
constexpr uint8_t kCmdTelem = 0x10;   // request telemetry snapshot

constexpr uint8_t kRspPong = 0x81;
constexpr uint8_t kRspAck = 0x82;
constexpr uint8_t kRspTelem = 0x90;
constexpr uint8_t kRspErr = 0xE0;

constexpr uint8_t kFlagImu = 1u << 0;
constexpr uint8_t kFlagMag = 1u << 1;
constexpr uint8_t kFlagIna = 1u << 2;

/** Fixed telemetry payload (little-endian), 42 bytes. */
struct __attribute__((packed)) TelemPayload {
  int32_t enc[4];
  uint16_t busMv;
  int16_t currentMa;
  int16_t axMg;
  int16_t ayMg;
  int16_t azMg;
  int16_t gxCdps;
  int16_t gyCdps;
  int16_t gzCdps;
  int16_t mxDeciUt;
  int16_t myDeciUt;
  int16_t mzDeciUt;
  int16_t tempCentiC;
  uint8_t flags;
  uint8_t reserved;
};

static_assert(sizeof(TelemPayload) == 42, "telem size");

inline uint8_t crc8(const uint8_t *data, uint8_t len) {
  uint16_t sum = 0;
  for (uint8_t i = 0; i < len; ++i) {
    sum = static_cast<uint16_t>(sum + data[i]);
  }
  return static_cast<uint8_t>(sum & 0xFF);
}

}  // namespace BinaryProtocol
