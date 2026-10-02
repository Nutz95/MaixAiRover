"""ObstacleNearMaskPanel reading thresholds."""

from __future__ import annotations

from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading


def test_reading_thresholds_order() -> None:
  reading = ObstacleBandReading(left=0.20, center=0.08, right=0.01)
  assert reading.left > reading.center > reading.right
