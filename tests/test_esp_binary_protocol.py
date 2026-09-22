"""Host unit checks for Maix↔ESP binary framing (no hardware / MaixPy)."""

from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.esp_binary_protocol import (
  CMD_PING,
  CMD_SPEED,
  CMD_TELEM,
  RSP_PONG,
  RSP_TELEM,
  SYNC,
  TELEM_SIZE,
  TELEM_STRUCT,
  crc8,
  encode_frame,
  try_parse_frame,
)
from lib.telem_snapshot import TelemSnapshot


def test_ping_roundtrip() -> None:
  frame = encode_frame(CMD_PING)
  assert frame[0] == SYNC
  assert frame[1] == CMD_PING
  assert frame[2] == 0
  assert frame[3] == crc8(frame[1:3])
  parsed = try_parse_frame(frame)
  assert parsed is not None
  msg_type, payload, rem = parsed
  assert msg_type == CMD_PING and payload == b"" and rem == b""


def test_speed_payload() -> None:
  body = struct.pack("bbbb", 20, -20, 0, 0)
  frame = encode_frame(CMD_SPEED, body)
  parsed = try_parse_frame(b"\x00\xff" + frame + b"extra")
  assert parsed is not None
  msg_type, payload, rem = parsed
  assert msg_type == CMD_SPEED
  assert payload == body
  assert rem == b"extra"


def test_bad_crc_resync() -> None:
  good = encode_frame(CMD_PING)
  bad = bytearray(good)
  bad[-1] ^= 0xFF
  # After bad frame, a good one should still parse.
  buf = bytes(bad) + good
  first = try_parse_frame(buf)
  # Bad SYNC path drops bytes until a valid frame is found.
  assert first is not None
  msg_type, payload, rem = first
  assert msg_type == CMD_PING and payload == b"" and rem == b""


def test_telem_layout() -> None:
  assert struct.calcsize(TELEM_STRUCT) == TELEM_SIZE == 42
  # Fake ESP TELEM payload: enc + ina + zeros/zeros.
  payload = struct.pack(
    TELEM_STRUCT,
    10,
    20,
    0,
    0,
    12000,
    -150,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    2500,
    0x07,  # imu|mag|ina
    0,
  )
  frame = encode_frame(RSP_TELEM, payload)
  parsed = try_parse_frame(frame)
  assert parsed is not None
  msg_type, body, _ = parsed
  assert msg_type == RSP_TELEM
  snap = TelemSnapshot.from_payload(body)
  assert snap.enc_fl == 10 and snap.enc_fr == 20
  assert snap.bus_mv == 12000 and snap.current_ma == -150
  assert snap.has_ina and snap.has_imu and snap.has_mag
  assert snap.temp_c == 25.0


def test_rsp_pong_constant() -> None:
  assert RSP_PONG == 0x81
  assert CMD_TELEM == 0x10


def main() -> None:
  test_ping_roundtrip()
  test_speed_payload()
  test_bad_crc_resync()
  test_telem_layout()
  test_rsp_pong_constant()
  print("esp_binary_protocol: ok")


if __name__ == "__main__":
  main()
