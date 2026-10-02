"""ObstacleBandReading column helpers."""

from __future__ import annotations

from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading


def test_reading_thresholds_order() -> None:
  reading = ObstacleBandReading(columns=[0.20, 0.12, 0.08, 0.04, 0.01])
  assert reading.left_mean() > reading.center_warmth() > reading.right_mean()
