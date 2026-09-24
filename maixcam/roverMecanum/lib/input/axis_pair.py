"""Strafe/forward axis pair for d-pad presets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AxisPair:
  """Strafe and forward axes on the ±32767 stick scale."""

  strafe: int = 0
  forward: int = 0
