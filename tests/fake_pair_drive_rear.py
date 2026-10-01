"""Fake rear pair board for DualBoardDrivePort host tests."""

from __future__ import annotations

from lib.motion.encoder_pair import EncoderPair
from fake_pair_drive_front import FakePairDriveFront


class FakePairDriveRear(FakePairDriveFront):
  """Same recorder as front; encoder ticks identify the rear axle."""

  def read_pair_encoders(self) -> EncoderPair:
    """Return fixed rear encoder sample."""
    return EncoderPair(left=3, right=4)
