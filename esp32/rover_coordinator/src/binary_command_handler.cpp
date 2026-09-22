#include "binary_command_handler.h"

#include <string.h>

#include "binary_protocol.h"
#include "board_sensors.h"
#include "coordinator_guard.h"
#include "coordinator_lock.h"
#include "drive_failsafe.h"
#include "front_drive_board.h"
#include "settings.h"

BinaryCommandHandler::BinaryCommandHandler(
  FrontDriveBoard &motors,
  DriveFailsafe &failsafe,
  BoardSensors &sensors,
  CoordinatorLock &lock)
  : motors_(motors), failsafe_(failsafe), sensors_(sensors), lock_(lock) {}

void BinaryCommandHandler::handle(
  Stream &out, uint8_t type, const uint8_t *payload, uint8_t len) {
  CoordinatorGuard guard(lock_);
  switch (type) {
    case BinaryProtocol::kCmdPing:
      sendFrame(out, BinaryProtocol::kRspPong, nullptr, 0);
      return;
    case BinaryProtocol::kCmdStop:
      motors_.stop();
      failsafe_.clear();
      sendAck(out, type);
      return;
    case BinaryProtocol::kCmdSpeed:
    case BinaryProtocol::kCmdPwm: {
      if (len < 4) {
        sendErr(out, 1);
        return;
      }
      const int8_t m1 = static_cast<int8_t>(payload[0]);
      const int8_t m2 = static_cast<int8_t>(payload[1]);
      const int8_t m3 = static_cast<int8_t>(payload[2]);
      const int8_t m4 = static_cast<int8_t>(payload[3]);
      const bool ok = (type == BinaryProtocol::kCmdPwm)
        ? motors_.setPwm(m1, m2, m3, m4)
        : motors_.setSpeed(m1, m2, m3, m4);
      if (!ok) {
        sendErr(out, 2);
        return;
      }
      if ((m1 | m2) != 0) {
        failsafe_.noteDriveActivity();
      } else {
        failsafe_.clear();
      }
      sendAck(out, type);
      return;
    }
    case BinaryProtocol::kCmdTelem:
      handleTelem(out);
      return;
    default:
      sendErr(out, 3);
      return;
  }
}

void BinaryCommandHandler::handleTelem(Stream &out) {
  BinaryProtocol::TelemPayload telem;
  sensors_.readInto(&telem);
  int32_t enc[4];
  if (motors_.readEncoders(enc)) {
    memcpy(telem.enc, enc, sizeof(enc));
  }
  sendFrame(
    out,
    BinaryProtocol::kRspTelem,
    reinterpret_cast<const uint8_t *>(&telem),
    static_cast<uint8_t>(sizeof(telem)));
}

void BinaryCommandHandler::sendAck(Stream &out, uint8_t reqType) {
  sendFrame(out, BinaryProtocol::kRspAck, &reqType, 1);
}

void BinaryCommandHandler::sendErr(Stream &out, uint8_t code) {
  sendFrame(out, BinaryProtocol::kRspErr, &code, 1);
}

void BinaryCommandHandler::sendFrame(
  Stream &out, uint8_t type, const uint8_t *payload, uint8_t len) {
  uint8_t body[2 + BinaryProtocol::kMaxPayload];
  if (len > BinaryProtocol::kMaxPayload) {
    len = BinaryProtocol::kMaxPayload;
  }
  body[0] = type;
  body[1] = len;
  if (payload != nullptr && len > 0) {
    memcpy(body + 2, payload, len);
  }
  const uint8_t crc = BinaryProtocol::crc8(body, static_cast<uint8_t>(2 + len));
  out.write(BinaryProtocol::kSync);
  out.write(body, 2 + len);
  out.write(crc);
}
