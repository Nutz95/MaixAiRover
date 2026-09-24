"""Incremental parser for Yahboom board→host frames (``FF FB …``)."""

from __future__ import annotations

import struct

from lib.yahboom.yahboom_battery import YahboomBattery
from lib.yahboom.yahboom_encoders import YahboomEncoders
from lib.yahboom.yahboom_imu_attitude import YahboomImuAttitude
from lib.yahboom.yahboom_protocol import (
  FUNC_REPORT_ENCODER,
  FUNC_REPORT_IMU_ATT,
  FUNC_REPORT_SPEED,
  HEAD,
  RX_DEVICE_ID,
)


class YahboomRxParser:
  """Parse auto-report speed/battery, IMU attitude, and encoder frames."""

  def __init__(self) -> None:
    self._buf = bytearray()
    self.last_imu: YahboomImuAttitude | None = None
    self.last_encoders: YahboomEncoders | None = None
    self.last_battery: YahboomBattery | None = None

  def feed(self, data: bytes) -> None:
    """Append bytes and extract complete frames."""
    if not data:
      return
    self._buf.extend(data)
    self._drain()

  def _drain(self) -> None:
    buf = self._buf
    while True:
      if len(buf) < 5:
        return
      try:
        start = buf.index(HEAD)
      except ValueError:
        buf.clear()
        return
      if start > 0:
        del buf[:start]
      if len(buf) < 5:
        return
      if buf[1] != RX_DEVICE_ID:
        del buf[0]
        continue
      ext_len = buf[2]
      frame_len = 1 + ext_len + 1
      if len(buf) < frame_len:
        return
      frame = bytes(buf[:frame_len])
      del buf[:frame_len]
      self._handle_frame(frame)

  def _handle_frame(self, frame: bytes) -> None:
    ext_len = frame[2]
    ext_type = frame[3]
    payload = frame[4:-1]
    rx_chk = frame[-1]
    check = (ext_len + ext_type + sum(payload)) & 0xFF
    if check != rx_chk:
      return
    if ext_type == FUNC_REPORT_SPEED and len(payload) >= 7:
      # vx,vy,vz int16 le + battery uint8 tenths of a volt
      tenths = struct.unpack_from("B", payload, 6)[0]
      self.last_battery = YahboomBattery(volts=tenths / 10.0)
    elif ext_type == FUNC_REPORT_IMU_ATT and len(payload) >= 6:
      roll, pitch, yaw = struct.unpack_from("<hhh", payload, 0)
      self.last_imu = YahboomImuAttitude(
        roll_deg=roll / 10000.0 * 57.2957795,
        pitch_deg=pitch / 10000.0 * 57.2957795,
        yaw_deg=yaw / 10000.0 * 57.2957795,
      )
    elif ext_type == FUNC_REPORT_ENCODER and len(payload) >= 16:
      m1, m2, m3, m4 = struct.unpack_from("<iiii", payload, 0)
      self.last_encoders = YahboomEncoders(m1=m1, m2=m2, m3=m3, m4=m4)
