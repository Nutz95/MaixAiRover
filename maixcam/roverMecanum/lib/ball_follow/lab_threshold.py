"""LAB threshold row for MaixPy find_blobs (Lmin..Bmax)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabThreshold:
  """One six-channel LAB threshold row for ``image.find_blobs``."""

  l_min: int
  l_max: int
  a_min: int
  a_max: int
  b_min: int
  b_max: int

  def as_maix_row(self) -> list[int]:
    """Return the six ints MaixPy ``find_blobs`` expects."""
    return [self.l_min, self.l_max, self.a_min, self.a_max, self.b_min, self.b_max]
