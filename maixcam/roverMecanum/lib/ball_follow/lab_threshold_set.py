"""Ordered LAB threshold rows for one ball color (no tuple DTO)."""

from __future__ import annotations

from lib.ball_follow.lab_threshold import LabThreshold


class LabThresholdSet:
  """Own one or more LAB rows for ``image.find_blobs``."""

  def __init__(self, rows: list[LabThreshold]) -> None:
    """Store a defensive copy of the LAB rows."""
    if not rows:
      raise ValueError("LabThresholdSet requires at least one LabThreshold")
    self._rows = list(rows)

  def maix_rows(self) -> list[list[int]]:
    """Rows for MaixPy ``find_blobs``."""
    return [row.as_maix_row() for row in self._rows]

  def first(self) -> LabThreshold:
    """Return the primary LAB row."""
    return self._rows[0]

  def count(self) -> int:
    """Return how many LAB rows are stored."""
    return len(self._rows)
