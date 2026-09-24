"""Host checks for Yahboom closed-loop frames + chassis mapping."""

from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.motion.chassis_velocity import ChassisVelocity
from lib.motion.drive_command import DriveCommand
from lib.motion.drive_command_chassis_mapper import DriveCommandChassisMapper
from lib.yahboom.yahboom_config import YahboomConfig
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard
from lib.yahboom.yahboom_protocol import (
  FUNC_MOTION,
  FUNC_SET_CAR_TYPE,
  HEAD,
  encode_car_motion,
  encode_set_car_type,
)
from lib.yahboom.yahboom_rx_parser import YahboomRxParser


class _MemTransport:
  def __init__(self) -> None:
    self.written: list[bytes] = []
    self._rx = b""

  def open(self) -> None:
    return

  def close(self) -> None:
    return

  def write(self, data: bytes) -> None:
    self.written.append(bytes(data))

  def read(self, max_len: int = 256) -> bytes:
    out = self._rx[:max_len]
    self._rx = self._rx[max_len:]
    return out


def test_encode_car_motion() -> None:
  frame = encode_car_motion(0x01, 0.5, -0.25, 1.0)
  assert frame[0] == HEAD
  assert frame[3] == FUNC_MOTION
  assert frame[4] == 0x01
  vx, vy, vz = struct.unpack_from("<hhh", frame, 5)
  assert vx == 500 and vy == -250 and vz == 1000


def test_encode_set_car_type() -> None:
  frame = encode_set_car_type(0x01)
  assert frame[3] == FUNC_SET_CAR_TYPE
  assert frame[4] == 0x01


def test_rx_imu_attitude() -> None:
  payload = struct.pack("<hhh", 0, 15708, 0)
  ext_len = 9
  frame_wo_chk = bytes([HEAD, 0xFB, ext_len, 0x0C]) + payload
  chk = (ext_len + 0x0C + sum(payload)) & 0xFF
  parser = YahboomRxParser()
  parser.feed(frame_wo_chk + bytes([chk]))
  assert parser.last_imu is not None
  assert abs(parser.last_imu.pitch_deg - 90.0) < 1.0


def test_drive_sends_car_motion_not_pwm() -> None:
  tx = _MemTransport()
  cfg = YahboomConfig(port="COM99", max_vx=1.0, max_vy=1.0, max_vz=5.0)
  board = YahboomDriveBoard(tx, cfg)
  board.initialize()
  board.set_velocity(ChassisVelocity(vx=0.5, vy=0.0, vz=0.0))
  motion_frames = [f for f in tx.written if len(f) >= 4 and f[3] == FUNC_MOTION]
  assert motion_frames, "expected set_car_motion frame"
  assert all(f[3] != 0x10 for f in tx.written if len(f) > 3 and f[3] in (0x10, FUNC_MOTION) or True)


def test_chassis_mapper_scales() -> None:
  cfg = YahboomConfig(port="", max_vx=1.0, max_vy=1.0, max_vz=5.0)
  mapper = DriveCommandChassisMapper(cfg)
  vel = mapper.map_command(DriveCommand(axis_forward=32767, max_speed=255))
  assert abs(vel.vx - 1.0) < 1e-3
  assert abs(vel.vy) < 1e-6
  # +strafe (RT / STRAFE_RIGHT) → Yahboom −vy (right).
  right = mapper.map_command(DriveCommand(axis_strafe=32767, max_speed=255))
  assert right.vy < 0
  left = mapper.map_command(DriveCommand(axis_strafe=-32767, max_speed=255))
  assert left.vy > 0
  # +spin (stick right) → Yahboom −vz (CW).
  cw = mapper.map_command(DriveCommand(axis_spin=32767, max_speed=255))
  assert cw.vz < 0


def main() -> None:
  test_encode_car_motion()
  test_encode_set_car_type()
  test_rx_imu_attitude()
  test_drive_sends_car_motion_not_pwm()
  test_chassis_mapper_scales()
  print("yahboom_protocol: ok")


if __name__ == "__main__":
  main()
