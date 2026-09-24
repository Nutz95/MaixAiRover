"""Port for applying four wheel setpoints (front/rear boards)."""

from __future__ import annotations

from typing import Protocol

from lib.motion.encoder_counts import EncoderCounts
from lib.motion.wheel_speeds import WheelSpeeds


class WheelDrivePort(Protocol):
  """Hardware or stub that can drive mecanum wheel setpoints."""

  def initialize(self, settle_s: float = 0.0) -> None:
    """Optional hardware init."""

  def set_wheel_speeds(self, speeds: WheelSpeeds) -> None:
    """Apply signed setpoints for FL/FR/RL/RR."""

  def stop(self) -> None:
    """Zero all channels."""

  def read_encoders(self) -> EncoderCounts:
    """Return encoder totals (zeros if unsupported)."""

  def clear_encoders(self) -> None:
    """Reset encoder totals when supported."""
