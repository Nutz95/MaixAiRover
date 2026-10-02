"""AvoidancePolicy strafe-first + corridor decisions (no Maix)."""

from __future__ import annotations

from lib.input.drive_output import DriveOutput
from lib.obstacle_nav.avoidance_hint import AvoidanceHint
from lib.obstacle_nav.avoidance_policy import AvoidancePolicy
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


def _settings() -> ObstacleNavSettings:
  return ObstacleNavSettings({
    "obstacle_nav": {
      "avoidance_enabled": True,
      "avoidance_close_warmth": 0.25,
      "avoidance_caution_warmth": 0.12,
      "avoidance_strafe_axis": 10000,
      "avoidance_reverse_axis": 7000,
    },
  })


def test_strafe_right_when_left_hot() -> None:
  policy = AvoidancePolicy()
  drive = DriveOutput(axis_forward=-5000)
  reading = ObstacleBandReading(columns=[0.40, 0.05, 0.0, 0.0, 0.0])
  decision = policy.decide(drive, reading, _settings())
  assert decision.hint is AvoidanceHint.STRAFE_RIGHT
  assert decision.drive.axis_strafe > 0


def test_reverse_when_all_hot() -> None:
  policy = AvoidancePolicy()
  drive = DriveOutput(axis_forward=-8000)
  reading = ObstacleBandReading(columns=[0.40, 0.40, 0.40, 0.40, 0.40])
  decision = policy.decide(drive, reading, _settings())
  assert decision.hint is AvoidanceHint.REVERSE
  assert decision.drive.axis_forward > 0


def test_corridor_keeps_forward() -> None:
  """Walls L/R with a free center lane must not panic-reverse."""
  policy = AvoidancePolicy()
  drive = DriveOutput(axis_forward=-8000)
  reading = ObstacleBandReading(columns=[0.45, 0.35, 0.05, 0.35, 0.45])
  decision = policy.decide(drive, reading, _settings())
  assert decision.hint is AvoidanceHint.NONE
  assert decision.drive.axis_forward == -8000
  assert decision.drive.axis_strafe == 0


def test_disabled_is_passthrough() -> None:
  settings = ObstacleNavSettings({"obstacle_nav": {"avoidance_enabled": False}})
  policy = AvoidancePolicy()
  drive = DriveOutput(axis_forward=-1000, axis_strafe=200)
  reading = ObstacleBandReading(columns=[0.9, 0.9, 0.9, 0.9, 0.9])
  decision = policy.decide(drive, reading, settings)
  assert decision.hint is AvoidanceHint.NONE
  assert decision.drive.axis_forward == -1000
