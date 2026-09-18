"""Touch screen press coordinates."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TouchPoint:
  """Single touch sample in display coordinates."""

  x: int
  y: int
