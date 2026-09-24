"""Yahboom board as closed-loop chassis port (encoders + PID on STM32)."""

from __future__ import annotations

import threading

from lib.yahboom.yahboom_protocol import (
  encode_auto_report,
  encode_car_motion,
  encode_set_car_type,
)
from lib.yahboom.yahboom_battery import YahboomBattery
from lib.yahboom.yahboom_rx_parser import YahboomRxParser
from lib.yahboom.yahboom_imu_attitude import YahboomImuAttitude
from lib.yahboom.yahboom_config import YahboomConfig
from lib.motion.byte_transport import ByteTransport
from lib.motion.chassis_velocity import ChassisVelocity
from lib.motion.encoder_counts import EncoderCounts


class YahboomDriveBoard:
  """``ChassisMotionPort`` over Rosmaster ``set_car_motion`` (not open-loop PWM).

  Channel silk for our rover (encoders reported M1..M4): FR, FL, RR, RL.

  USB I/O is serialized on ``_io_lock``. HUD getters only read the last
  parsed sample (no USB) so display never blocks on CH340 bulk transfers.
  """

  def __init__(self, transport: ByteTransport, config: YahboomConfig) -> None:
    self._tx = transport
    self._config = config
    self._parser = YahboomRxParser()
    self._last: ChassisVelocity | None = None
    self._open = False
    self._io_lock = threading.Lock()

  def initialize(self, settle_s: float = 0.0) -> None:
    """Open USB serial, select mecanum profile, enable IMU/encoder reports."""
    del settle_s
    with self._io_lock:
      self._tx.open()
      self._open = True
      self._tx.write(encode_set_car_type(self._config.car_type))
      self._tx.write(encode_auto_report(True, forever=False))
      self._pump_rx_unlocked()
    self.stop()

  def set_velocity(self, velocity: ChassisVelocity) -> None:
    """Send closed-loop body velocity (board uses encoders + PID)."""
    with self._io_lock:
      self._pump_rx_unlocked()
      if self._last is not None and (
        abs(self._last.vx - velocity.vx) < 1e-4
        and abs(self._last.vy - velocity.vy) < 1e-4
        and abs(self._last.vz - velocity.vz) < 1e-4
      ):
        return
      self._tx.write(
        encode_car_motion(
          self._config.car_type,
          velocity.vx,
          velocity.vy,
          velocity.vz,
        )
      )
      self._last = velocity

  def stop(self) -> None:
    """Zero chassis velocity."""
    self.set_velocity(ChassisVelocity())

  def read_encoders(self) -> EncoderCounts:
    """Cached encoders remapped to FL/FR/RL/RR (no USB; call ``poll`` to refresh)."""
    with self._io_lock:
      enc = self._parser.last_encoders
      if enc is None:
        return EncoderCounts()
      # Board M1=FR, M2=FL, M3=RR, M4=RL → EncoderCounts.m1..m4 = FL,FR,RL,RR.
      return EncoderCounts(m1=enc.m2, m2=enc.m1, m3=enc.m4, m4=enc.m3)

  def clear_encoders(self) -> None:
    """Not exposed by Rosmaster host protocol — no-op."""
    return

  def poll(self) -> None:
    """Pump RX once under the I/O lock (teleop / checklist / DBG)."""
    with self._io_lock:
      self._pump_rx_unlocked()

  def refresh_reports(self) -> None:
    """Re-assert mecanum profile + auto-report (DBG INIT)."""
    with self._io_lock:
      self._tx.write(encode_set_car_type(self._config.car_type))
      self._tx.write(encode_auto_report(True, forever=False))
      self._pump_rx_unlocked()

  def has_encoder_report(self) -> bool:
    """True once at least one encoder auto-report frame was parsed."""
    with self._io_lock:
      return self._parser.last_encoders is not None

  def battery(self) -> YahboomBattery | None:
    """Cached pack voltage (no USB)."""
    with self._io_lock:
      return self._parser.last_battery

  def imu_attitude(self) -> YahboomImuAttitude | None:
    """Cached attitude (no USB)."""
    with self._io_lock:
      return self._parser.last_imu

  def close(self) -> None:
    """Stop motors and close transport."""
    try:
      if self._open:
        self.stop()
    except Exception as swallowed:
      print(f"yahboom_drive_board.py: {swallowed}")
    with self._io_lock:
      self._tx.close()
      self._open = False

  def _pump_rx_unlocked(self) -> None:
    try:
      chunk = self._tx.read(512)
    except Exception as read_error:
      print(f"yahboom: rx: {read_error}")
      return
    if chunk:
      self._parser.feed(chunk)
