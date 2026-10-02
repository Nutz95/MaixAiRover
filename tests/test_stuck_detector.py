"""StuckDetector side hints from synthetic IMU / accel / command windows."""

from __future__ import annotations

from lib.obstacle_nav.collision_side import CollisionSide
from lib.obstacle_nav.imu_chassis_frame import ImuChassisFrame
from lib.obstacle_nav.motion_probe_sample import MotionProbeSample
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings
from lib.obstacle_nav.stuck_cause import StuckCause
from lib.obstacle_nav.stuck_detector import StuckDetector
from lib.obstacle_nav.stuck_level import StuckLevel
from lib.obstacle_nav.stuck_report import StuckReport


def _settings(**overrides) -> ObstacleNavSettings:
  block = {
    "enabled": True,
    "stuck_window_ms": 300,
    "yaw_error_deg": 25,
    "pitch_lift_deg": 15,
    "roll_bump_deg": 12,
    "cmd_axis_threshold": 800,
    "encoder_tick_threshold": 3,
    "accel_impact_mps2": 3.0,
    "accel_crash_mps2": 5.0,
    "impact_hold_ms": 150,
    "soft_impact_enabled": False,
    "accel_launch_mps2": 0.45,
    "slip_delta_v_mps": 0.10,
    "slip_enabled": False,
    **overrides,
  }
  return ObstacleNavSettings({"obstacle_nav": block})


def _sample(
  ms: int,
  *,
  pitch: float = 0.0,
  roll: float = 0.0,
  yaw: float = 0.0,
  ax: float = 0.0,
  ay: float = 0.0,
  az: float = 9.8,
  enc: int = 0,
  fwd: int = 0,
  spin: int = 0,
  strafe: int = 0,
  accel_valid: bool = True,
) -> MotionProbeSample:
  return MotionProbeSample(
    timestamp_ms=ms,
    pitch_deg=pitch,
    roll_deg=roll,
    yaw_deg=yaw,
    ax=ax,
    ay=ay,
    az=az,
    encoder_sum=enc,
    axis_forward=fwd,
    axis_spin=spin,
    axis_strafe=strafe,
    accel_valid=accel_valid,
  )


def test_idle_when_no_command() -> None:
  detector = StuckDetector(_settings())
  detector.update(_sample(0, enc=0, fwd=0))
  report = detector.update(_sample(300, enc=20, fwd=0))
  assert report.level == StuckLevel.OK


def test_idle_pitch_tip_is_detected() -> None:
  """Lifting nose/tail with sticks idle must raise stuck."""
  detector = StuckDetector(_settings())
  detector.set_frame(ImuChassisFrame.default())
  detector.update(_sample(0, pitch=0.0, fwd=0))
  report = detector.update(_sample(50, pitch=18.0, fwd=0))
  assert report.level == StuckLevel.STUCK
  assert report.side == CollisionSide.FRONT
  assert "pitch" in report.detail
  assert report.cause == StuckCause.ATTITUDE_TIP
  assert report.cuts_drive()


def test_small_pitch_bob_while_driving_ok() -> None:
  detector = StuckDetector(_settings())
  detector.set_frame(ImuChassisFrame.default())
  detector.update(_sample(0, pitch=0.0, enc=0, fwd=-5000))
  report = detector.update(_sample(300, pitch=8.0, enc=40, fwd=-5000))
  assert report.level == StuckLevel.OK


def test_launch_accel_is_not_impact() -> None:
  detector = StuckDetector(_settings())
  detector.set_frame(ImuChassisFrame.default())
  detector.update(_sample(0, ax=0.0, enc=0, fwd=-5000))
  report = detector.update(_sample(300, ax=2.0, enc=40, fwd=-5000))
  assert report.level == StuckLevel.OK


def test_brief_soft_opposing_is_ignored() -> None:
  """Cruise settle / vibe below crash threshold must not popup (soft off)."""
  detector = StuckDetector(_settings())
  detector.set_frame(ImuChassisFrame.default())
  detector.update(_sample(0, ax=1.5, enc=0, fwd=-5000))
  report = detector.update(_sample(40, ax=-3.5, enc=20, fwd=-5000))
  assert report.level == StuckLevel.OK
  report = detector.update(_sample(200, ax=-3.5, enc=40, fwd=-5000))
  assert report.level == StuckLevel.OK


def test_violent_crash_is_instant() -> None:
  detector = StuckDetector(_settings())
  detector.set_frame(ImuChassisFrame.default())
  detector.update(_sample(0, ax=0.0, enc=0, fwd=-5000))
  report = detector.update(_sample(40, ax=-6.0, enc=10, fwd=-5000))
  assert report.level == StuckLevel.STUCK
  assert report.side == CollisionSide.FRONT
  assert "crash" in report.detail
  assert report.cause == StuckCause.CRASH
  assert not report.cuts_drive()


def test_soft_impact_when_enabled_needs_hold() -> None:
  detector = StuckDetector(_settings(soft_impact_enabled=True, impact_hold_ms=120))
  detector.set_frame(ImuChassisFrame.default())
  detector.update(_sample(0, ax=0.0, enc=0, fwd=-5000))
  detector.update(_sample(50, ax=-3.5, enc=10, fwd=-5000))
  report = detector.update(_sample(100, ax=-3.5, enc=20, fwd=-5000))
  assert report.level == StuckLevel.OK
  report = detector.update(_sample(200, ax=-3.5, enc=30, fwd=-5000))
  assert report.level == StuckLevel.STUCK
  assert report.side == CollisionSide.FRONT


def test_slip_disabled_by_default() -> None:
  detector = StuckDetector(_settings())
  detector.set_frame(ImuChassisFrame.default())
  report = StuckReport.clear()
  for i, enc in enumerate((0, 20, 40, 60, 80)):
    report = detector.update(
      _sample(i * 100, ax=0.05, ay=0.02, enc=enc, fwd=5000),
    )
  assert report.level == StuckLevel.OK
