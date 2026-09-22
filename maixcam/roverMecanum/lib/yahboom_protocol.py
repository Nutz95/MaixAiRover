"""Yahboom Rosmaster binary frames (FF FC) — closed-loop encode helpers."""

from __future__ import annotations

import struct

HEAD = 0xFF
DEVICE_ID = 0xFC
COMPLEMENT = 257 - DEVICE_ID  # 1
RX_DEVICE_ID = DEVICE_ID - 1  # 0xFB

FUNC_AUTO_REPORT = 0x01
FUNC_REPORT_IMU_ATT = 0x0C
FUNC_REPORT_ENCODER = 0x0D
FUNC_MOTION = 0x12
FUNC_SET_CAR_TYPE = 0x15


def _checksum(cmd_without_chk: list[int]) -> int:
  return (sum(cmd_without_chk) + COMPLEMENT) & 0xFF


def encode_frame(func: int, payload: bytes) -> bytes:
  """Build ``FF FC LEN FUNC …payload… CHK`` (LEN = len(cmd)-1 before CHK)."""
  cmd = [HEAD, DEVICE_ID, 0x00, func & 0xFF]
  cmd.extend(payload)
  cmd[2] = len(cmd) - 1
  cmd.append(_checksum(cmd))
  return bytes(cmd)


def encode_car_motion(car_type: int, vx: float, vy: float, vz: float) -> bytes:
  """Closed-loop chassis command (STM32 mixes + PID on encoders)."""
  payload = bytes([int(car_type) & 0xFF]) + struct.pack(
    "<hhh",
    int(vx * 1000.0),
    int(vy * 1000.0),
    int(vz * 1000.0),
  )
  return encode_frame(FUNC_MOTION, payload)


def encode_set_car_type(car_type: int) -> bytes:
  """Select kinematics profile (mecanum X3 = 0x01); ``0x5F`` = persist."""
  return encode_frame(FUNC_SET_CAR_TYPE, bytes((int(car_type) & 0xFF, 0x5F)))


def encode_auto_report(enable: bool, forever: bool = False) -> bytes:
  """Enable/disable MCU auto telemetry stream."""
  state1 = 1 if enable else 0
  state2 = 0x5F if forever else 0
  return encode_frame(FUNC_AUTO_REPORT, bytes((state1, state2)))
