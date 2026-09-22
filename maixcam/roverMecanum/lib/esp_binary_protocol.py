"""Try to parse one SYNC frame; drop bad sync bytes without inventing replies."""

from __future__ import annotations

SYNC = 0xA5
MAX_PAYLOAD = 64

CMD_PING = 0x01
CMD_STOP = 0x02
CMD_SPEED = 0x03
CMD_PWM = 0x04
CMD_TELEM = 0x10

RSP_PONG = 0x81
RSP_ACK = 0x82
RSP_TELEM = 0x90
RSP_ERR = 0xE0

FLAG_IMU = 1 << 0
FLAG_MAG = 1 << 1
FLAG_INA = 1 << 2

TELEM_STRUCT = "<4iHh6h3hhBB"
TELEM_SIZE = 42


def crc8(data: bytes) -> int:
  """Return sum(data) & 0xFF (matches ESP BinaryProtocol::crc8)."""
  return sum(data) & 0xFF


def encode_frame(msg_type: int, payload: bytes = b"") -> bytes:
  """Build SYNC TYPE LEN PAYLOAD CRC8."""
  if len(payload) > MAX_PAYLOAD:
    raise ValueError("payload too long")
  body = bytes((msg_type & 0xFF, len(payload))) + payload
  return bytes((SYNC,)) + body + bytes((crc8(body),))


def try_parse_frame(buf: bytes) -> tuple[int, bytes, bytes] | None:
  """
  Parse one frame from ``buf``.

  Returns ``(type, payload, remainder)``, or None if more bytes are needed.
  On bad CRC / oversized LEN, drops the SYNC and retries on the rest.
  """
  while True:
    start = buf.find(bytes((SYNC,)))
    if start < 0:
      return None
    if start > 0:
      buf = buf[start:]
    if len(buf) < 4:
      return None
    msg_type = buf[1]
    length = buf[2]
    if length > MAX_PAYLOAD:
      buf = buf[1:]
      continue
    need = 3 + length + 1
    if len(buf) < need:
      return None
    body = buf[1 : 3 + length]
    crc = buf[3 + length]
    remainder = buf[need:]
    if crc != crc8(body):
      buf = buf[1:]
      continue
    return (msg_type, body[2:], remainder)


def _self_check() -> None:
  import struct

  frame = encode_frame(CMD_PING)
  assert frame[0] == SYNC
  parsed = try_parse_frame(frame)
  assert parsed is not None
  msg_type, payload, rem = parsed
  assert msg_type == CMD_PING and payload == b"" and rem == b""
  assert struct.calcsize(TELEM_STRUCT) == TELEM_SIZE


_self_check()
