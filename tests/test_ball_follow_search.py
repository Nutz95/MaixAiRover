"""Ball-follow lost-ball encoder search phase (no MaixPy)."""

from lib.ball_follow.ball_follow_policy import BallFollowPolicy
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_observation import BallObservation


def _settings(**overrides):
  raw = {
    "ball_follow": {
      "search_turn_deg": 360,
      "search_turn_ms": 500,
      "lost_search_ms": 500,
      "search_pause_ms": 50,
      "search_retreat_ms": 200,
      "compass_fix_tolerance_deg": 5,
      "compass_fix_timeout_ms": 2000,
      "forward_axis_sign": 1,
      "spin_axis_sign": 1,
      **overrides,
    }
  }
  return BallFollowSettings(raw)


def _obs(now_ms: int, x_ratio: float = 0.5) -> BallObservation:
  width = 320
  return BallObservation(
    center_x=int(x_ratio * width),
    center_y=120,
    width=40,
    height=40,
    area=1600,
    score=1.0,
    timestamp_ms=now_ms,
    image_width=width,
    image_height=240,
  )


def test_encoder_search_reaches_360_then_compass() -> None:
  """After lost wait, encoder yaw accum completes spin then compass_fix."""
  policy = BallFollowPolicy(_settings())
  cmd = policy.decide(_obs(0), 0, yaw_deg=10.0)
  assert cmd.reason in ("align", "approach", "target_distance", "too_close")
  cmd = policy.decide(None, 100, yaw_deg=10.0)
  assert cmd.reason == "target_lost"
  cmd = policy.decide(None, 600, yaw_deg=10.0, encoder_yaw_delta_deg=0.0)
  assert cmd.reason == "search"
  cmd = policy.decide(None, 700, yaw_deg=10.0, encoder_yaw_delta_deg=180.0)
  assert cmd.reason == "search"
  cmd = policy.decide(None, 800, yaw_deg=40.0, encoder_yaw_delta_deg=180.0)
  assert cmd.reason in ("compass_fix", "search_pause")


def test_timed_fallback_when_encoders_stall() -> None:
  """Missing encoder deltas still finish via 3× search_turn_ms."""
  policy = BallFollowPolicy(_settings(search_turn_ms=500))
  policy.decide(_obs(0), 0, yaw_deg=0.0)
  policy.decide(None, 100, yaw_deg=0.0)
  policy.decide(None, 600, yaw_deg=0.0, encoder_yaw_delta_deg=None)
  cmd = policy.decide(None, 700, yaw_deg=0.0, encoder_yaw_delta_deg=None)
  assert cmd.reason == "search"
  cmd = policy.decide(None, 600 + 500 * 3, yaw_deg=90.0, encoder_yaw_delta_deg=None)
  assert cmd.reason in ("compass_fix", "search_pause")


if __name__ == "__main__":
  test_encoder_search_reaches_360_then_compass()
  test_timed_fallback_when_encoders_stall()
  print("ball_follow_search: ok")
