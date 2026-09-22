"""Port for closed-loop chassis velocity (board mixes + uses encoders)."""

from __future__ import annotations

from typing import Protocol

from lib.chassis_velocity import ChassisVelocity
from lib.encoder_counts import EncoderCounts


class ChassisMotionPort(Protocol):
  """Hardware that accepts body-frame velocity (not open-loop wheel PWM)."""

  def initialize(self, settle_s: float = 0.0) -> None:
    """Optional hardware init."""

  def set_velocity(self, velocity: ChassisVelocity) -> None:
    """Apply signed body-frame velocity."""

  def stop(self) -> None:
    """Zero motion."""

  def read_encoders(self) -> EncoderCounts:
    """Return encoder totals (zeros if unsupported)."""

  def clear_encoders(self) -> None:
    """Reset encoder totals when supported."""
