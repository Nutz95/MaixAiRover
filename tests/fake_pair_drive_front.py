"""Fake front pair board for DualBoardDrivePort host tests."""

from __future__ import annotations

from lib.motion.encoder_pair import EncoderPair


class FakePairDriveFront:
  """Records set_pair calls; returns fixed front encoder ticks."""

  def __init__(self) -> None:
    """Start with an empty command log."""
    self.pairs: list = []
    self.stopped = 0

  def initialize(self, settle_s: float = 0.0) -> None:
    """No-op init (host double)."""
    del settle_s

  def set_pair(self, left: int, right: int) -> None:
    """Record one left/right setpoint."""
    self.pairs.append((left, right))

  def stop(self) -> None:
    """Count stops and record a zero pair."""
    self.stopped += 1
    self.pairs.append((0, 0))

  def read_pair_encoders(self) -> EncoderPair:
    """Return fixed front encoder sample."""
    return EncoderPair(left=1, right=2)

  def clear_encoders(self) -> None:
    """No-op clear."""
    return
