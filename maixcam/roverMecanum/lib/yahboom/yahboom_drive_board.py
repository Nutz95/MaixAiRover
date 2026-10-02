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
from lib.yahboom.yahboom_imu_accel import YahboomImuAccel
from lib.yahboom.yahboom_imu_attitude import YahboomImuAttitude
from lib.yahboom.yahboom_config import YahboomConfig
from lib.motion.byte_transport import ByteTransport
from lib.motion.chassis_velocity import ChassisVelocity
from lib.motion.encoder_counts import EncoderCounts


class YahboomDriveBoard:
  """``ChassisMotionPort`` over Rosmaster ``set_car_motion`` (not open-loop PWM).

  Firmware channel map (Yahboom docs §12/§15): M1=FL, M2=RL, M3=FR, M4=RR.
  Wiring must match, otherwise ``vz`` spins front-vs-rear instead of yaw.

  USB I/O is serialized on ``_io_lock``. HUD getters only read the last
  parsed sample (no USB) so display never blocks on CH340 bulk transfers.
  """

  def __init__(self, transport: ByteTransport, config: YahboomConfig) -> None:
    self._tx = transport
    self._config = config
    self._parser = YahboomRxParser()
    self._last: ChassisVelocity | None = None
    self._open = False
    self._last_error = ""
    self._io_lock = threading.Lock()

  @property
  def is_open(self) -> bool:
    """True after a successful USB open / init."""
    return self._open

  @property
  def last_error(self) -> str:
    """Last open/init failure text (empty when healthy)."""
    return self._last_error

  def initialize(self, settle_s: float = 0.0) -> None:
    """Open USB serial, select mecanum profile, enable IMU/encoder reports."""
    del settle_s
    try:
      with self._io_lock:
        self._tx.open()
        self._open = True
        self._last_error = ""
        self._tx.write(encode_set_car_type(self._config.car_type))
        self._tx.write(encode_auto_report(True, forever=False))
        self._pump_rx_unlocked()
      self.stop()
    except Exception as open_error:
      self._last_error = str(open_error)
      self._open = False
      try:
        self._tx.close()
      except Exception as close_error:
        print(f"yahboom init close: {close_error}")
      raise

  def try_open(self) -> bool:
    """Re-attempt USB open after a missing CH340 / bad cable.

    Returns True on success. Sets ``last_error`` when it fails.
    """
    if self._open:
      return True
    try:
      try:
        self._tx.close()
      except Exception as close_error:
        print(f"yahboom try_open close: {close_error}")
      self.initialize()
      return True
    except Exception as open_error:
      print(f"yahboom try_open: {open_error}")
      return False

  def set_velocity(self, velocity: ChassisVelocity) -> None:
    """Send closed-loop body velocity (board uses encoders + PID)."""
    with self._io_lock:
      if not self._open:
        return
      try:
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
      except Exception as io_error:
        self._drop_link_unlocked(str(io_error))

  def stop(self) -> None:
    """Zero chassis velocity."""
    self.set_velocity(ChassisVelocity())

  def read_encoders(self) -> EncoderCounts:
    """Cached encoders remapped to FL/FR/RL/RR (no USB; call ``poll`` to refresh)."""
    with self._io_lock:
      enc = self._parser.last_encoders
      if enc is None:
        return EncoderCounts()
      # Board M1=FL, M2=RL, M3=FR, M4=RR → EncoderCounts.m1..m4 = FL,FR,RL,RR.
      return EncoderCounts(m1=enc.m1, m2=enc.m3, m3=enc.m2, m4=enc.m4)

  def clear_encoders(self) -> None:
    """Not exposed by Rosmaster host protocol — no-op."""
    return

  def poll(self) -> None:
    """Pump RX once under the I/O lock (teleop / checklist / DBG)."""
    with self._io_lock:
      if not self._open:
        return
      try:
        self._pump_rx_unlocked()
      except Exception as io_error:
        self._drop_link_unlocked(str(io_error))

  def refresh_reports(self) -> None:
    """Re-assert mecanum profile + auto-report (DBG INIT)."""
    with self._io_lock:
      if not self._open:
        return
      try:
        self._tx.write(encode_set_car_type(self._config.car_type))
        self._tx.write(encode_auto_report(True, forever=False))
        self._pump_rx_unlocked()
      except Exception as io_error:
        self._drop_link_unlocked(str(io_error))

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

  def imu_accel(self) -> YahboomImuAccel | None:
    """Cached accelerometer (no USB; from MPU/ICM raw auto-report)."""
    with self._io_lock:
      return self._parser.last_accel

  def close(self) -> None:
    """Stop motors and close transport."""
    try:
      if self._open:
        self.stop()
    except Exception as swallowed:
      print(f"yahboom_drive_board.py: {swallowed}")
    with self._io_lock:
      self._drop_link_unlocked("")

  def _drop_link_unlocked(self, reason: str) -> None:
    """Mark USB dead and close transport (caller holds ``_io_lock``)."""
    was_open = self._open
    if reason:
      self._last_error = reason
    elif not self._last_error:
      self._last_error = "USB link lost"
    self._open = False
    self._last = None
    try:
      self._tx.close()
    except Exception as close_error:
      print(f"yahboom drop close: {close_error}")
    if was_open and reason:
      print(f"yahboom: link lost ({self._last_error})")

  def _pump_rx_unlocked(self) -> None:
    chunk = self._tx.read(512)
    if chunk:
      self._parser.feed(chunk)
