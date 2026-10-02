"""IMU calib wizard state machine (no motors)."""

from __future__ import annotations

from lib.obstacle_nav.imu_calib_step import ImuCalibStep
from lib.obstacle_nav.imu_calib_wizard import ImuCalibWizard
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


def _wizard() -> ImuCalibWizard:
  settings = ObstacleNavSettings(
    {
      "obstacle_nav": {
        "calib_skippable": True,
        "calib_rest_ms": 100,
        "calib_motion_ms": 100,
        "calib_creep_axis": 5000,
        "calib_spin_axis": 6000,
      }
    }
  )
  return ImuCalibWizard(settings)


def test_intro_requires_confirm_before_motion() -> None:
  wizard = _wizard()
  wizard.start(0)
  snap = wizard.snapshot()
  assert snap.step == ImuCalibStep.INTRO
  assert snap.can_confirm
  drive = wizard.tick(50, pitch_deg=1.0, roll_deg=0.0, yaw_deg=0.0)
  assert drive is not None
  assert drive.axis_forward == 0
  wizard.confirm(100)
  assert wizard.snapshot().step == ImuCalibStep.REST


def test_skip_yields_default_frame() -> None:
  wizard = _wizard()
  wizard.start(0)
  wizard.skip()
  assert wizard.snapshot().step == ImuCalibStep.SKIPPED
  frame = wizard.frame()
  assert frame.pitch_forward_sign == 1.0
  assert frame.yaw_spin_sign == 1.0


def test_full_script_learns_pitch_and_yaw_signs() -> None:
  wizard = _wizard()
  wizard.start(0)
  wizard.confirm(0)
  # REST
  wizard.tick(50, pitch_deg=2.0, roll_deg=1.0, yaw_deg=10.0)
  assert wizard.snapshot().step == ImuCalibStep.REST
  wizard.tick(150, pitch_deg=2.0, roll_deg=1.0, yaw_deg=10.0)
  # FORWARD — pitch rises
  assert wizard.snapshot().step == ImuCalibStep.FORWARD
  drive = wizard.tick(160, pitch_deg=2.0, roll_deg=1.0, yaw_deg=10.0)
  assert drive is not None and drive.axis_forward < 0
  wizard.tick(260, pitch_deg=5.0, roll_deg=1.0, yaw_deg=10.0)
  # REVERSE
  assert wizard.snapshot().step == ImuCalibStep.REVERSE
  wizard.tick(270, pitch_deg=4.0, roll_deg=1.0, yaw_deg=10.0)
  wizard.tick(370, pitch_deg=3.0, roll_deg=1.0, yaw_deg=10.0)
  # SPIN_CW — yaw increases
  assert wizard.snapshot().step == ImuCalibStep.SPIN_CW
  wizard.tick(380, pitch_deg=3.0, roll_deg=1.0, yaw_deg=10.0)
  wizard.tick(480, pitch_deg=3.0, roll_deg=1.0, yaw_deg=40.0)
  # SPIN_CCW → DONE
  assert wizard.snapshot().step == ImuCalibStep.SPIN_CCW
  wizard.tick(490, pitch_deg=3.0, roll_deg=1.0, yaw_deg=35.0)
  wizard.tick(590, pitch_deg=3.0, roll_deg=1.0, yaw_deg=5.0)
  snap = wizard.snapshot()
  assert snap.step == ImuCalibStep.DONE
  assert snap.can_confirm
  assert wizard.is_active()
  frame = wizard.frame()
  assert frame.pitch0_deg == 2.0
  assert frame.roll0_deg == 1.0
  assert frame.pitch_forward_sign == 1.0
  assert frame.yaw_spin_sign == 1.0
  wizard.confirm(600)
  assert not wizard.is_active()
  assert wizard.snapshot().step == ImuCalibStep.IDLE
