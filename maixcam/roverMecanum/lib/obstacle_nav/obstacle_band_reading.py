"""L/C/R mean turbo warmth in the obstacle ROI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObstacleBandReading:
  """Warmth means in the obstacle corridor (higher = closer / warmer)."""

  left: float
  center: float
  right: float

  @staticmethod
  def clear() -> ObstacleBandReading:
    """Return a cold (empty) reading."""
    return ObstacleBandReading(left=0.0, center=0.0, right=0.0)
