"""Per-column turbo warmth across the obstacle ROI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObstacleBandReading:
  """Column warmths left→right (higher = closer / warmer)."""

  columns: list[float]

  @staticmethod
  def clear(column_count: int = 5) -> ObstacleBandReading:
    """Return a cold reading with ``column_count`` zero columns."""
    count = max(1, int(column_count))
    return ObstacleBandReading(columns=[0.0] * count)

  def column_count(self) -> int:
    """Return how many vertical bands were sampled."""
    return len(self.columns)

  def warmth_at(self, index: int) -> float:
    """Return warmth for one column index."""
    return self.columns[index]

  def mean_range(self, start: int, end: int) -> float:
    """Mean warmth over ``columns[start:end]`` (empty → 0)."""
    chunk = self.columns[start:end]
    if not chunk:
      return 0.0
    return sum(chunk) / len(chunk)

  def left_mean(self) -> float:
    """Mean of the left half (excludes the center column when odd)."""
    mid = self.column_count() // 2
    return self.mean_range(0, mid)

  def center_warmth(self) -> float:
    """Warmth of the middle column."""
    return self.columns[self.column_count() // 2]

  def right_mean(self) -> float:
    """Mean of the right half (excludes the center column when odd)."""
    mid = self.column_count() // 2
    return self.mean_range(mid + 1, self.column_count())

  def hud_label(self) -> str:
    """Compact HUD string of column warmths."""
    parts = [f"{warmth:.2f}" for warmth in self.columns]
    return "OBS " + " ".join(parts)
