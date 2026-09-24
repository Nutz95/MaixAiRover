"""Left/right encoder pair for a single drive board."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EncoderPair:
  """Signed encoder totals for one board's left and right motors."""

  left: int = 0
  right: int = 0
