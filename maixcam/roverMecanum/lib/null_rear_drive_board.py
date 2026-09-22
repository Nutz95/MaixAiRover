"""Rear drive board stub until the second controller is wired."""

from __future__ import annotations

from lib.encoder_pair import EncoderPair


class NullRearDriveBoard:
  """Accepts RL/RR setpoints and discards them (rear board not present)."""

  def initialize(self, settle_s: float = 0.0) -> None:
    """No hardware."""
    del settle_s

  def set_pair(self, left: int, right: int) -> None:
    """Ignore rear setpoints for now."""
    del left, right

  def stop(self) -> None:
    """No-op."""
    return

  def read_pair_encoders(self) -> EncoderPair:
    """Rear encoders unavailable."""
    return EncoderPair()

  def clear_encoders(self) -> None:
    """No-op."""
    return
