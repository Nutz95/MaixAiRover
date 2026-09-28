"""Ball-follow lost-ball encoder/IMU search phase (no MaixPy)."""

from lib.ball_follow.ball_follow_policy import BallFollowPolicy
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_observation import BallObservation


def _settings(**overrides):
  raw = {
    "ball_follow": {
      "color": "green",
      "color_order": ["green", "red"],
      "colors": {
        "green": [[40, 90, -90, -40, 25, 75]],
        "red": [[0, 80, 40, 80, 10, 80]],
      },
      "search_turn_deg": 360,
      "search_turn_ms": 500,
      "lost_search_ms": 500,
      "search_pause_ms": 50,
      "search_retreat_ms": 200,
      "compass_fix_tolerance_deg": 5,
      "compass_fix_timeout_ms": 2000,
      "forward_axis_sign": -1,
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


def _drive_to_reason(policy, start_ms: int, yaw_deg: float, want, encoder=None):
  """Advance lost-ball ticks until reason matches (or timeout)."""
  t = start_ms
  cmd = None
  for _ in range(80):
    kwargs = {"yaw_deg": yaw_deg}
    if encoder is not None:
      kwargs["encoder_yaw_delta_deg"] = encoder
    cmd = policy.decide(None, t, **kwargs)
    if cmd.reason in want:
      return t, cmd
    t += 50
  return t, cmd


def test_lost_retreats_before_spin() -> None:
  """After lost wait, first motion is reverse — not an immediate 360°."""
  from lib.motion.drive_command import DriveCommand
  from lib.motion.drive_command_chassis_mapper import DriveCommandChassisMapper
  from lib.yahboom.yahboom_config import YahboomConfig

  policy = BallFollowPolicy(_settings())
  policy.decide(_obs(0), 0, yaw_deg=0.0)
  policy.decide(None, 10, yaw_deg=0.0)  # enter lost_wait
  # lost_search_ms floor is 500
  cmd = policy.decide(None, 500, yaw_deg=0.0)
  assert cmd.reason == "search_retreat"
  assert cmd.forward > 0
  mapper = DriveCommandChassisMapper(YahboomConfig(port=""))
  vel = mapper.map_command(DriveCommand(axis_forward=cmd.forward, max_speed=255))
  assert vel.vx < 0


def test_imu_search_reaches_360_then_compass() -> None:
  """After retreat+pause, IMU yaw accum completes spin (then compass or pause)."""
  policy = BallFollowPolicy(_settings())
  policy.decide(_obs(0), 0, yaw_deg=0.0)
  policy.decide(None, 10, yaw_deg=0.0)
  t, cmd = _drive_to_reason(policy, 500, 0.0, ("search_retreat",))
  assert cmd.reason == "search_retreat"
  t, cmd = _drive_to_reason(policy, t + 50, 0.0, ("search",))
  assert cmd.reason == "search"
  yaw = 0.0
  for _ in range(20):
    yaw += 30.0
    t += 50
    cmd = policy.decide(None, t, yaw_deg=yaw % 360.0)
    if cmd.reason in ("compass_fix", "search_pause"):
      break
  # Heading already matches start after a full turn → often jumps to pause.
  assert cmd.reason in ("compass_fix", "search_pause")
  assert policy._imu_yaw_accum >= 360.0


def test_encoder_fallback_when_imu_flat() -> None:
  """Encoder yaw still completes search if IMU heading is stuck."""
  policy = BallFollowPolicy(_settings())
  policy.decide(_obs(0), 0, yaw_deg=10.0)
  policy.decide(None, 10, yaw_deg=10.0)
  t, cmd = _drive_to_reason(policy, 500, 10.0, ("search",), encoder=0.0)
  assert cmd.reason == "search"
  for _ in range(20):
    t += 40
    cmd = policy.decide(None, t, yaw_deg=10.0, encoder_yaw_delta_deg=40.0)
    if cmd.reason in ("compass_fix", "search_pause"):
      break
  assert cmd.reason in ("compass_fix", "search_pause")
  assert policy._encoder_yaw_accum >= 360.0


def test_timed_fallback_when_sensors_stall() -> None:
  """Missing yaw deltas still finish via stall_mult × search_turn_ms."""
  policy = BallFollowPolicy(_settings(search_turn_stall_mult=3))
  policy.decide(_obs(0), 0, yaw_deg=0.0)
  policy.decide(None, 10, yaw_deg=0.0)
  t, cmd = _drive_to_reason(policy, 500, 0.0, ("search",))
  assert cmd.reason == "search"
  spin_start = t
  # stall = 500 * 3 = 1500ms since phase_started at enter_search_spin
  cmd = policy.decide(None, spin_start + 1500, yaw_deg=90.0)
  assert cmd.reason in ("compass_fix", "search_pause")


if __name__ == "__main__":
  test_lost_retreats_before_spin()
  test_imu_search_reaches_360_then_compass()
  test_encoder_fallback_when_imu_flat()
  test_timed_fallback_when_sensors_stall()
  print("ball_follow_search: ok")
