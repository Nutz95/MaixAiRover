"""Named ball color preset loaded from config.json."""

from __future__ import annotations

from dataclasses import dataclass

from lib.ball_follow.lab_threshold_set import LabThresholdSet


@dataclass(frozen=True)
class BallColorPreset:
  """One named color (e.g. green/red) with LAB thresholds."""

  name: str
  thresholds: LabThresholdSet

  def maix_thresholds(self) -> list[list[int]]:
    """Rows for ``image.find_blobs``."""
    return self.thresholds.maix_rows()
