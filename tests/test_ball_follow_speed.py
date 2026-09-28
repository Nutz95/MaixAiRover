"""Ball-follow Y-setpoint approach / retreat / lateral spin."""

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
      "target_center_y_ratio": 0.60,
      "target_y_tolerance_ratio": 0.06,
      "target_height_ratio": 0.22,
      "target_tolerance_ratio": 0.07,
      "too_close_height_ratio": 0.40,
      "too_close_center_y_ratio": 0.90,
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
      "forward_axis_sign": -1,
      "spin_axis_sign": 1,
      **overrides,
    }
  }
  return BallFollowSettings(raw)


def _obs(
  now_ms: int,
  *,
  x_ratio: float = 0.5,
  y_ratio: float = 0.60,
  height_ratio: float = 0.22,
  image_height: int = 240,
) -> BallObservation:
  width = 320
  height = max(1, int(height_ratio * image_height))
  return BallObservation(
    center_x=int(x_ratio * width),
    center_y=int(y_ratio * image_height),
    width=40,
    height=height,
    area=40 * height,
    score=1.0,
    timestamp_ms=now_ms,
    image_width=width,
    image_height=image_height,
  )


def test_ball_high_in_frame_approaches() -> None:
  """Ball above the 3/5 band → drive forward."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.35, height_ratio=0.12), 0)
  assert cmd.reason == "approach"
  assert cmd.forward < 0


def test_ball_below_setpoint_retreats() -> None:
  """Ball below the 3/5 band → reverse before it exits the frame."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.75, height_ratio=0.18), 0)
  assert cmd.reason == "too_close"
  assert cmd.forward > 0


def test_y_hold_band_stops() -> None:
  """Inside ±tol around 0.60 → stop (formation held)."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.60), 0)
  assert cmd.reason == "target_distance"
  assert cmd.forward == 0


def test_y_hold_hysteresis_avoids_pump() -> None:
  """Once holding, small Y noise inside exit band stays stopped."""
  policy = BallFollowPolicy(_settings())
  assert policy.decide(_obs(0, y_ratio=0.60), 0).reason == "target_distance"
  # exit band = 0.60 ± 0.12 → 0.50 still holds
  still = policy.decide(_obs(50, y_ratio=0.50), 50)
  assert still.reason == "target_distance"
  assert still.forward == 0


def test_hard_bumper_y_triggers_retreat() -> None:
  """Hard bottom edge still emergency-reverses."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.92, height_ratio=0.14), 0)
  assert cmd.reason == "too_close"
  assert cmd.forward > 0


def test_loss_at_or_below_setpoint_retreats_immediately() -> None:
  """Losing the ball at/below Y setpoint skips lost wait."""
  policy = BallFollowPolicy(_settings(lost_search_ms=2000, search_retreat_ms=500))
  policy.decide(_obs(0, y_ratio=0.70), 0)
  lost = policy.decide(None, 20)
  assert lost.reason == "search_retreat"
  assert lost.forward > 0


def test_align_while_low_also_retreats() -> None:
  """Off-center + below band → spin and reverse together (no chase-down)."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, x_ratio=0.80, y_ratio=0.78), 0)
  assert cmd.spin != 0
  assert cmd.forward > 0


def test_align_while_high_creeps_forward() -> None:
  """Off-center + above band → spin and approach together."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, x_ratio=0.80, y_ratio=0.30, height_ratio=0.10), 0)
  assert cmd.reason == "align"
  assert cmd.spin != 0
  assert cmd.forward < 0


def test_far_approach_faster_than_near_retreat() -> None:
  """High in frame → stronger forward; just below band → gentler reverse."""
  policy = BallFollowPolicy(_settings())
  far = policy.decide(_obs(0, y_ratio=0.15), 0)
  assert far.reason == "approach"
  assert far.forward < -8000

  close = policy.decide(_obs(50, y_ratio=0.72), 50)
  assert close.reason == "too_close"
  assert close.forward > 0
  assert abs(close.forward) < abs(far.forward)
  assert abs(close.forward) <= 2800


def test_fast_lateral_velocity_boosts_spin() -> None:
  """A fast sideways slide raises align spin vs a static off-center ball."""
  policy = BallFollowPolicy(_settings())
  policy.decide(_obs(0, x_ratio=0.50, y_ratio=0.60), 0)
  slow = policy.decide(_obs(100, x_ratio=0.70, y_ratio=0.60), 100)
  assert slow.reason == "align"
  assert slow.spin != 0

  policy2 = BallFollowPolicy(_settings())
  policy2.decide(_obs(0, x_ratio=0.20, y_ratio=0.60), 0)
  fast = policy2.decide(_obs(50, x_ratio=0.85, y_ratio=0.60), 50)
  assert fast.reason == "align"
  assert abs(fast.spin) >= abs(slow.spin)
