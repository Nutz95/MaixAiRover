"""Scripted IMU rest / creep / spin calibration after pad connect."""

from __future__ import annotations

from lib.input.drive_output import DriveOutput
from lib.obstacle_nav.imu_calib_snapshot import ImuCalibSnapshot
from lib.obstacle_nav.imu_calib_step import ImuCalibStep
from lib.obstacle_nav.imu_chassis_frame import ImuChassisFrame
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


class ImuCalibWizard:
  """Drive short motions and learn pitch/yaw/accel signs vs chassis axes."""

  def __init__(self, settings: ObstacleNavSettings) -> None:
    """Create an idle wizard."""
    self._settings = settings
    self._step = ImuCalibStep.IDLE
    self._step_started_ms = 0
    self._pitch0 = 0.0
    self._roll0 = 0.0
    self._ax0 = 0.0
    self._ay0 = 0.0
    self._az0 = 9.8
    self._pitch_at_fwd_start = 0.0
    self._pitch_fwd_peak = 0.0
    self._accel_peak = (0.0, 0.0, 0.0)
    self._yaw_at_spin_start = 0.0
    self._yaw_cw_delta = 0.0
    self._live_pitch = 0.0
    self._live_roll = 0.0
    self._live_yaw = 0.0
    self._live_ax = 0.0
    self._live_ay = 0.0
    self._live_az = 0.0
    self._frame = ImuChassisFrame.default()
    self._awaiting_confirm = False

  def apply_settings(self, settings: ObstacleNavSettings) -> None:
    """Hot-reload motion durations / axis magnitudes."""
    self._settings = settings

  def is_active(self) -> bool:
    """True while the wizard owns the HUD (incl. DONE awaiting dismiss)."""
    if self._step == ImuCalibStep.DONE:
      return self._awaiting_confirm
    return self._step not in (
      ImuCalibStep.IDLE,
      ImuCalibStep.SKIPPED,
    )

  def blocks_drive(self) -> bool:
    """True when teleop sticks must not drive (wizard owns motors or waits)."""
    return self.is_active()

  def frame(self) -> ImuChassisFrame:
    """Return the last learned or default chassis frame."""
    return self._frame

  def reset(self) -> None:
    """Return to idle without starting."""
    self._step = ImuCalibStep.IDLE
    self._awaiting_confirm = False
    self._frame = ImuChassisFrame.default()

  def start(self, now_ms: int) -> None:
    """Open the intro screen (user must confirm before motion)."""
    self._step = ImuCalibStep.INTRO
    self._step_started_ms = now_ms
    self._awaiting_confirm = True
    self._pitch0 = 0.0
    self._roll0 = 0.0
    self._ax0 = 0.0
    self._ay0 = 0.0
    self._az0 = 9.8
    self._pitch_fwd_peak = 0.0
    self._accel_peak = (0.0, 0.0, 0.0)
    self._yaw_cw_delta = 0.0

  def skip(self) -> None:
    """Abort and keep the default chassis frame."""
    if not self._settings.calib_skippable and self.is_active():
      return
    self._frame = ImuChassisFrame.default()
    self._step = ImuCalibStep.SKIPPED
    self._awaiting_confirm = False

  def confirm(self, now_ms: int) -> None:
    """Advance from a waiting intro / done screen."""
    if self._step == ImuCalibStep.INTRO and self._awaiting_confirm:
      self._awaiting_confirm = False
      self._enter(ImuCalibStep.REST, now_ms)
      return
    if self._step == ImuCalibStep.DONE and self._awaiting_confirm:
      self._awaiting_confirm = False
      self._step = ImuCalibStep.IDLE

  def snapshot(self) -> ImuCalibSnapshot:
    """Build the current panel content."""
    title, detail = self._copy_for_step()
    progress = self._progress_ratio()
    return ImuCalibSnapshot(
      step=self._step,
      title=title,
      detail=detail,
      pitch_deg=self._live_pitch,
      roll_deg=self._live_roll,
      yaw_deg=self._live_yaw,
      can_confirm=self._awaiting_confirm,
      can_skip=(
        self._settings.calib_skippable
        and self.is_active()
        and self._step != ImuCalibStep.DONE
      ),
      progress_ratio=progress,
    )

  def tick(
    self,
    now_ms: int,
    *,
    pitch_deg: float,
    roll_deg: float,
    yaw_deg: float,
    ax: float = 0.0,
    ay: float = 0.0,
    az: float = 9.8,
  ) -> DriveOutput | None:
    """Advance timed steps; return a drive override or None when waiting."""
    self._live_pitch = pitch_deg
    self._live_roll = roll_deg
    self._live_yaw = yaw_deg
    self._live_ax = ax
    self._live_ay = ay
    self._live_az = az
    if not self.is_active():
      return None
    if self._awaiting_confirm:
      return DriveOutput()
    if self._step == ImuCalibStep.REST:
      return self._tick_rest(now_ms, pitch_deg, roll_deg, ax, ay, az)
    if self._step == ImuCalibStep.FORWARD:
      return self._tick_forward(now_ms, pitch_deg, ax, ay, az)
    if self._step == ImuCalibStep.REVERSE:
      return self._tick_reverse(now_ms)
    if self._step == ImuCalibStep.SPIN_CW:
      return self._tick_spin_cw(now_ms, yaw_deg)
    if self._step == ImuCalibStep.SPIN_CCW:
      return self._tick_spin_ccw(now_ms)
    return DriveOutput()

  def _enter(self, step: ImuCalibStep, now_ms: int) -> None:
    self._step = step
    self._step_started_ms = now_ms
    self._awaiting_confirm = False

  def _elapsed(self, now_ms: int) -> int:
    return max(0, now_ms - self._step_started_ms)

  def _progress_ratio(self) -> float:
    order = [
      ImuCalibStep.INTRO,
      ImuCalibStep.REST,
      ImuCalibStep.FORWARD,
      ImuCalibStep.REVERSE,
      ImuCalibStep.SPIN_CW,
      ImuCalibStep.SPIN_CCW,
      ImuCalibStep.DONE,
    ]
    if self._step not in order:
      return 0.0
    return order.index(self._step) / float(len(order) - 1)

  def _tick_rest(
    self,
    now_ms: int,
    pitch_deg: float,
    roll_deg: float,
    ax: float,
    ay: float,
    az: float,
  ) -> DriveOutput:
    if self._elapsed(now_ms) >= self._settings.calib_rest_ms:
      self._pitch0 = pitch_deg
      self._roll0 = roll_deg
      self._ax0 = ax
      self._ay0 = ay
      self._az0 = az
      self._pitch_at_fwd_start = pitch_deg
      self._accel_peak = (0.0, 0.0, 0.0)
      self._enter(ImuCalibStep.FORWARD, now_ms)
    return DriveOutput()

  def _tick_forward(
    self,
    now_ms: int,
    pitch_deg: float,
    ax: float,
    ay: float,
    az: float,
  ) -> DriveOutput:
    delta = pitch_deg - self._pitch_at_fwd_start
    if abs(delta) > abs(self._pitch_fwd_peak):
      self._pitch_fwd_peak = delta
    dax = ax - self._ax0
    day = ay - self._ay0
    daz = az - self._az0
    peak = list(self._accel_peak)
    if abs(dax) > abs(peak[0]):
      peak[0] = dax
    if abs(day) > abs(peak[1]):
      peak[1] = day
    if abs(daz) > abs(peak[2]):
      peak[2] = daz
    self._accel_peak = (peak[0], peak[1], peak[2])
    if self._elapsed(now_ms) >= self._settings.calib_motion_ms:
      self._enter(ImuCalibStep.REVERSE, now_ms)
    return DriveOutput(axis_forward=-self._settings.calib_creep_axis)

  def _tick_reverse(self, now_ms: int) -> DriveOutput:
    if self._elapsed(now_ms) >= self._settings.calib_motion_ms:
      self._yaw_at_spin_start = self._live_yaw
      self._enter(ImuCalibStep.SPIN_CW, now_ms)
    return DriveOutput(axis_forward=self._settings.calib_creep_axis)

  def _tick_spin_cw(self, now_ms: int, yaw_deg: float) -> DriveOutput:
    self._yaw_cw_delta = self._yaw_delta(self._yaw_at_spin_start, yaw_deg)
    if self._elapsed(now_ms) >= self._settings.calib_motion_ms:
      self._enter(ImuCalibStep.SPIN_CCW, now_ms)
    return DriveOutput(axis_spin=self._settings.calib_spin_axis)

  def _tick_spin_ccw(self, now_ms: int) -> DriveOutput:
    if self._elapsed(now_ms) >= self._settings.calib_motion_ms:
      self._finish()
      return DriveOutput()
    return DriveOutput(axis_spin=-self._settings.calib_spin_axis)

  def _finish(self) -> None:
    pitch_sign = 1.0
    if abs(self._pitch_fwd_peak) >= 0.3:
      pitch_sign = 1.0 if self._pitch_fwd_peak > 0 else -1.0
    yaw_sign = 1.0
    if abs(self._yaw_cw_delta) >= 1.0:
      yaw_sign = 1.0 if self._yaw_cw_delta > 0 else -1.0
    peak = self._accel_peak
    axis = 0
    if abs(peak[1]) >= abs(peak[0]) and abs(peak[1]) >= abs(peak[2]):
      axis = 1
    elif abs(peak[2]) >= abs(peak[0]) and abs(peak[2]) >= abs(peak[1]):
      axis = 2
    accel_sign = 1.0
    if abs(peak[axis]) >= 0.15:
      accel_sign = 1.0 if peak[axis] > 0 else -1.0
    self._frame = ImuChassisFrame(
      pitch0_deg=self._pitch0,
      roll0_deg=self._roll0,
      pitch_forward_sign=pitch_sign,
      yaw_spin_sign=yaw_sign,
      ax0=self._ax0,
      ay0=self._ay0,
      az0=self._az0,
      forward_accel_axis=axis,
      forward_accel_sign=accel_sign,
    )
    self._step = ImuCalibStep.DONE
    self._awaiting_confirm = True
    print(
      "imu calib:"
      f" pitch0={self._pitch0:.1f} roll0={self._roll0:.1f}"
      f" a0=({self._ax0:.2f},{self._ay0:.2f},{self._az0:.2f})"
      f" fwd_axis={axis} a_sign={accel_sign}"
      f" pitch_sign={pitch_sign} yaw_sign={yaw_sign}"
    )

  def _copy_for_step(self) -> tuple[str, str]:
    if self._step == ImuCalibStep.INTRO:
      return (
        "IMU calibration",
        "Clear space. A/OK starts. Skip=defaults.",
      )
    if self._step == ImuCalibStep.REST:
      return ("Hold still", "Sampling rest attitude + accel")
    if self._step == ImuCalibStep.FORWARD:
      return ("Creep forward", "Learning forward accel axis")
    if self._step == ImuCalibStep.REVERSE:
      return ("Creep reverse", "Settling")
    if self._step == ImuCalibStep.SPIN_CW:
      return ("Spin CW", "Learning yaw sign")
    if self._step == ImuCalibStep.SPIN_CCW:
      return ("Spin CCW", "Finishing")
    if self._step == ImuCalibStep.DONE:
      return (
        "Calibration done",
        (
          f"a_axis={self._frame.forward_accel_axis}"
          f" a_sign={self._frame.forward_accel_sign:+.0f}"
          f" pitch_sign={self._frame.pitch_forward_sign:+.0f}"
        ),
      )
    return ("IMU calibration", "")

  @staticmethod
  def _yaw_delta(start_deg: float, now_deg: float) -> float:
    return (now_deg - start_deg + 180.0) % 360.0 - 180.0
