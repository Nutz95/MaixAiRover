"""Ball-follow approach / retreat / lateral spin speed shaping."""

from __future__ import annotations

from lib.ball_follow.ball_follow_policy import BallFollowPolicy
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_observation import BallObservation


def _settings(**overrides) -> BallFollowSettings:
  raw = {
    "ball_follow": {
      "color": "green",
      "color_order": ["green", "red"],
      "colors": {
        "green": [[40, 90, -90, -40, 25, 75]],
        "red": [[0, 80, 40, 80, 10, 80]],
      },
      "target_height_ratio": 0.22,
      "target_tolerance_ratio": 0.07,
      "too_close_height_ratio": 0.40,
      "horizontal_deadzone": 0.12,
      "min_forward_axis": 1500,
      "max_forward_axis": 15000,
      "max_retreat_axis": 2800,
      "min_spin_axis": 1200,
      "max_spin_axis": 9000,
      "forward_gain": 30000,
      "spin_gain": 14000,
      "spin_damping": 2800,
      "exit_velocity_threshold": 0.05,
      "forward_axis_sign": 1,
      "spin_axis_sign": 1,
      **overrides,
    }
  }
  return BallFollowSettings(raw)


def _obs(
  now_ms: int,
  *,
  x_ratio: float = 0.5,
  height_ratio: float = 0.22,
  image_height: int = 240,
) -> BallObservation:
  width = 320
  height = max(1, int(height_ratio * image_height))
  return BallObservation(
    center_x=int(x_ratio * width),
    center_y=120,
    width=40,
    height=height,
    area=40 * height,
    score=1.0,
    timestamp_ms=now_ms,
    image_width=width,
    image_height=image_height,
  )


def test_far_approach_faster_than_near_retreat() -> None:
  """Far blob → stronger forward; just-too-close → gentle reverse."""
  policy = BallFollowPolicy(_settings())
  far = policy.decide(_obs(0, height_ratio=0.06), 0)
  assert far.reason == "approach"
  assert far.forward > 8000

  close = policy.decide(_obs(50, height_ratio=0.42), 50)
  assert close.reason == "too_close"
  assert close.forward < 0
  assert abs(close.forward) < abs(far.forward)
  assert abs(close.forward) <= 2800


def test_fast_lateral_velocity_boosts_spin() -> None:
  """A fast sideways slide raises align spin vs a static off-center ball."""
  policy = BallFollowPolicy(_settings())
  policy.decide(_obs(0, x_ratio=0.50), 0)
  slow = policy.decide(_obs(100, x_ratio=0.70), 100)
  assert slow.reason == "align"
  assert slow.spin != 0

  policy2 = BallFollowPolicy(_settings())
  policy2.decide(_obs(0, x_ratio=0.20), 0)
  # Huge lateral jump in 50 ms → high velocity_x.
  fast = policy2.decide(_obs(50, x_ratio=0.85), 50)
  assert fast.reason == "align"
  assert abs(fast.spin) >= abs(slow.spin)


def test_align_while_far_also_creeps_forward() -> None:
  """Off-center + far → spin and a non-zero approach crawl."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, x_ratio=0.80, height_ratio=0.08), 0)
  assert cmd.reason == "align"
  assert cmd.spin != 0
  assert cmd.forward > 0
