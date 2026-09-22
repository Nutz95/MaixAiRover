"""Yahboom board as closed-loop chassis port (encoders + PID on STM32)."""

from __future__ import annotations

from lib.yahboom_protocol import (
  encode_auto_report,
  encode_car_motion,
  encode_set_car_type,
)
from lib.yahboom_rx_parser import YahboomRxParser
from lib.yahboom_imu_attitude import YahboomImuAttitude
from lib.yahboom_config import YahboomConfig
from lib.byte_transport import ByteTransport
from lib.chassis_velocity import ChassisVelocity
from lib.encoder_counts import EncoderCounts


class YahboomDriveBoard:
  """``ChassisMotionPort`` over Rosmaster ``set_car_motion`` (not open-loop PWM).

  Channel silk for our rover (encoders reported M1..M4): FR, FL, RR, RL.
  """

  def __init__(self, transport: ByteTransport, config: YahboomConfig) -> None:
    self._tx = transport
    self._config = config
    self._parser = YahboomRxParser()
    self._last: ChassisVelocity | None = None
    self._open = False

  def initialize(self, settle_s: float = 0.0) -> None:
    """Open USB serial, select mecanum profile, enable IMU/encoder reports."""
    del settle_s
    self._tx.open()
    self._open = True
    self._tx.write(encode_set_car_type(self._config.car_type))
    self._tx.write(encode_auto_report(True, forever=False))
    self._poll_rx()
    self.stop()

  def set_velocity(self, velocity: ChassisVelocity) -> None:
    """Send closed-loop body velocity (board uses encoders + PID)."""
    self._poll_rx()
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
    """Last encoder report remapped to FL/FR/RL/RR field names on EncoderCounts."""
    self._poll_rx()
    enc = self._parser.last_encoders
    if enc is None:
      return EncoderCounts()
    # Board M1=FR, M2=FL, M3=RR, M4=RL → EncoderCounts.m1..m4 = FL,FR,RL,RR legacy order.
    return EncoderCounts(m1=enc.m2, m2=enc.m1, m3=enc.m4, m4=enc.m3)

  def clear_encoders(self) -> None:
    """Not exposed by Rosmaster host protocol — no-op."""
    return

  def imu_attitude(self) -> YahboomImuAttitude | None:
    """Latest attitude sample, if any."""
    self._poll_rx()
    return self._parser.last_imu

  def close(self) -> None:
    """Stop motors and close transport."""
    try:
      if self._open:
        self.stop()
    except Exception:
      pass
    self._tx.close()
    self._open = False

  def _poll_rx(self) -> None:
    try:
      chunk = self._tx.read(512)
    except Exception:
      return
    self._parser.feed(chunk)
