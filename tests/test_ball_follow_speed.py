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
      "target_center_y_ratio": 0.50,
      "target_y_tolerance_ratio": 0.06,
      "target_height_ratio": 0.22,
      "target_tolerance_ratio": 0.07,
      "too_close_height_ratio": 0.40,
      "too_close_center_y_ratio": 0.90,
      "horizontal_deadzone": 0.06,
      "min_forward_axis": 1500,
      "max_forward_axis": 15000,
      "max_retreat_axis": 2800,
      "min_spin_axis": 1200,
      "max_spin_axis": 9000,
      "forward_gain": 30000,
      "spin_gain": 14000,
      "spin_damping": 2800,
      "align_spin_full_error": 0.22,
      "align_spin_curve": 0.55,
      "align_spin_velocity_boost": 1.5,
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
  y_ratio: float = 0.50,
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
  """Ball above mid-frame band → drive forward."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.30, height_ratio=0.12), 0)
  assert cmd.reason == "approach"
  assert cmd.forward < 0


def test_ball_below_setpoint_retreats() -> None:
  """Ball below mid-frame band → reverse before it exits the frame."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.70, height_ratio=0.18), 0)
  assert cmd.reason == "too_close"
  assert cmd.forward > 0


def test_y_hold_band_stops() -> None:
  """Inside ±tol around 0.50 → stop (formation held)."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.50), 0)
  assert cmd.reason == "target_distance"
  assert cmd.forward == 0


def test_y_hold_hysteresis_avoids_pump() -> None:
  """Once holding, small Y noise inside exit band stays stopped."""
  policy = BallFollowPolicy(_settings(target_y_tolerance_ratio=0.03))
  assert policy.decide(_obs(0, y_ratio=0.50), 0).reason == "target_distance"
  # exit band = 0.50 ± 0.06 → 0.45 still holds
  still = policy.decide(_obs(50, y_ratio=0.45), 50)
  assert still.reason == "target_distance"
  assert still.forward == 0


def test_aggressive_retreat_curve_backs_harder_than_ease_in() -> None:
  """curve 0.40 retreats harder than ease-in 1.2 just below the Y band."""
  soft = BallFollowPolicy(
    _settings(
      target_y_tolerance_ratio=0.03,
      retreat_curve=1.2,
      max_retreat_axis=10000,
      retreat_soft_cap_ratio=1.0,
    ),
  )
  firm = BallFollowPolicy(
    _settings(
      target_y_tolerance_ratio=0.03,
      retreat_curve=0.40,
      max_retreat_axis=10000,
      retreat_soft_cap_ratio=1.0,
    ),
  )
  # Just below enter_hi (0.53): soft ease-in stays mild; 0.40 climbs early.
  soft_cmd = soft.decide(_obs(0, y_ratio=0.58, height_ratio=0.22), 0)
  firm_cmd = firm.decide(_obs(0, y_ratio=0.58, height_ratio=0.22), 0)
  assert soft_cmd.reason == "too_close" and firm_cmd.reason == "too_close"
  assert abs(firm_cmd.forward) > abs(soft_cmd.forward)


def test_hard_bumper_y_triggers_retreat() -> None:
  """Hard bottom edge still emergency-reverses."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, y_ratio=0.92, height_ratio=0.14), 0)
  assert cmd.reason == "too_close"
  assert cmd.forward > 0


def test_loss_at_or_below_setpoint_retreats_immediately() -> None:
  """Losing the ball at/below Y setpoint skips lost wait."""
  policy = BallFollowPolicy(_settings(lost_search_ms=2000, search_retreat_ms=500))
  policy.decide(_obs(0, y_ratio=0.65), 0)
  lost = policy.decide(None, 20)
  assert lost.reason == "search_retreat"
  assert lost.forward > 0


def test_align_while_low_also_retreats() -> None:
  """Off-center + below band → spin and reverse together (no chase-down)."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, x_ratio=0.80, y_ratio=0.72), 0)
  assert cmd.spin != 0
  assert cmd.forward > 0


def test_align_while_high_creeps_forward() -> None:
  """Off-center + above band → spin and approach together."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0, x_ratio=0.80, y_ratio=0.25, height_ratio=0.10), 0)
  assert cmd.reason == "align"
  assert cmd.spin != 0
  assert cmd.forward < 0


def test_far_from_center_spins_harder_than_near() -> None:
  """Larger X offset → stronger spin (position-only align)."""
  policy = BallFollowPolicy(_settings())
  near = policy.decide(_obs(0, x_ratio=0.62, y_ratio=0.50), 0)
  far = policy.decide(_obs(50, x_ratio=0.88, y_ratio=0.50), 50)
  assert near.reason == "align" and far.reason == "align"
  assert abs(far.spin) > abs(near.spin)


def test_aggressive_curve_spins_harder_near_center_than_ease_in() -> None:
  """curve < 1 responds earlier than ease-in (>1) at the same small X error."""
  soft = BallFollowPolicy(
    _settings(align_spin_curve=1.15, align_spin_full_error=0.22, horizontal_deadzone=0.04),
  )
  firm = BallFollowPolicy(
    _settings(align_spin_curve=0.55, align_spin_full_error=0.22, horizontal_deadzone=0.04),
  )
  # Just outside deadzone: ease-in stays under the soft floor; 0.55 already climbs.
  soft_cmd = soft.decide(_obs(0, x_ratio=0.55, y_ratio=0.50, height_ratio=0.22), 0)
  firm_cmd = firm.decide(_obs(0, x_ratio=0.55, y_ratio=0.50, height_ratio=0.22), 0)
  assert soft_cmd.reason == "align" and firm_cmd.reason == "align"
  assert abs(firm_cmd.spin) > abs(soft_cmd.spin)


def test_closer_ball_spins_harder_than_far_ball() -> None:
  """Same X error: larger blob (closer) → stronger yaw than a tiny far blob."""
  policy = BallFollowPolicy(
    _settings(target_height_ratio=0.22, align_spin_curve=0.55, align_spin_full_error=0.22),
  )
  far = policy.decide(_obs(0, x_ratio=0.78, y_ratio=0.45, height_ratio=0.10), 0)
  close = policy.decide(_obs(50, x_ratio=0.78, y_ratio=0.45, height_ratio=0.32), 50)
  assert far.reason == "align" and close.reason == "align"
  assert abs(close.spin) > abs(far.spin)


def test_align_ignores_image_velocity() -> None:
  """Same X error + size → same spin whether the blob slid fast or slow."""
  policy = BallFollowPolicy(_settings(align_spin_curve=0.55))
  policy.decide(_obs(0, x_ratio=0.50, y_ratio=0.50, height_ratio=0.22), 0)
  slow = policy.decide(_obs(200, x_ratio=0.70, y_ratio=0.50, height_ratio=0.22), 200)
  policy2 = BallFollowPolicy(_settings(align_spin_curve=0.55))
  policy2.decide(_obs(0, x_ratio=0.20, y_ratio=0.50, height_ratio=0.22), 0)
  fast = policy2.decide(_obs(40, x_ratio=0.70, y_ratio=0.50, height_ratio=0.22), 40)
  assert slow.reason == "align" and fast.reason == "align"
  assert abs(slow.spin) == abs(fast.spin)


def test_exit_search_uses_last_free_motion_velocity() -> None:
  """Velocity sampled while not spinning still picks search direction on loss."""
  policy = BallFollowPolicy(
    _settings(lost_search_ms=2000, search_retreat_ms=500, exit_velocity_threshold=0.05),
  )
  # Centered → no spin → next frame may update free-motion velocity.
  policy.decide(_obs(0, x_ratio=0.50, y_ratio=0.40), 0)
  policy.decide(_obs(50, x_ratio=0.78, y_ratio=0.40), 50)
  assert policy._velocity_x > 0
  policy.decide(None, 60)
  assert policy._search_spin_sign == policy._settings.spin_axis_sign * 1


def test_far_approach_faster_than_near_retreat() -> None:
  """High in frame → stronger forward; just below band → gentler reverse."""
  policy = BallFollowPolicy(_settings())
  far = policy.decide(_obs(0, y_ratio=0.15), 0)
  assert far.reason == "approach"
  assert far.forward < -8000

  close = policy.decide(_obs(50, y_ratio=0.65), 50)
  assert close.reason == "too_close"
  assert close.forward > 0
  assert abs(close.forward) < abs(far.forward)
  assert abs(close.forward) <= 2800
