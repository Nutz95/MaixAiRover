"""Own IMU calib wizard + stuck detector for the app loop."""

from __future__ import annotations

from maix import time

from lib.input.drive_output import DriveOutput
from lib.motion.encoder_counts import EncoderCounts
from lib.obstacle_nav.imu_calib_panel import ImuCalibPanel
from lib.obstacle_nav.imu_calib_snapshot import ImuCalibSnapshot
from lib.obstacle_nav.imu_calib_step import ImuCalibStep
from lib.obstacle_nav.imu_calib_wizard import ImuCalibWizard
from lib.obstacle_nav.imu_chassis_frame import ImuChassisFrame
from lib.obstacle_nav.motion_probe_sample import MotionProbeSample
from lib.obstacle_nav.nav_roi_guide_panel import NavRoiGuidePanel
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings
from lib.obstacle_nav.obstacle_probe_hub import ObstacleProbeHub
from lib.obstacle_nav.stuck_detector import StuckDetector
from lib.obstacle_nav.stuck_level import StuckLevel
from lib.obstacle_nav.stuck_overlay_panel import StuckOverlayPanel
from lib.obstacle_nav.stuck_probe import StuckProbe
from lib.obstacle_nav.stuck_report import StuckReport
from lib.yahboom.yahboom_imu_accel import YahboomImuAccel
from lib.yahboom.yahboom_imu_attitude import YahboomImuAttitude


class ObstacleNavRuntime:
  """Calib after checklist, then always-on stuck awareness."""

  def __init__(self, width: int, height: int, raw_config: dict) -> None:
    """Build panels and detectors from config."""
    self._settings = ObstacleNavSettings(raw_config)
    self._wizard = ImuCalibWizard(self._settings)
    self._detector = StuckDetector(self._settings)
    self._calib_panel = ImuCalibPanel(width, height)
    self._stuck_panel = StuckOverlayPanel(width, height)
    self._roi_guide_panel = NavRoiGuidePanel()
    self._report = StuckReport.clear()
    self._overlay_visible = False
    self._clear_since_ms: int | None = None
    self._last_cmd = DriveOutput()
    self._ready_for_stuck = False
    self._last_probe_log_ms = 0
    self._probe_hub: ObstacleProbeHub | None = None
    if self._settings.enabled and self._settings.probe_tcp_port > 0:
      self._probe_hub = ObstacleProbeHub(self._settings.probe_tcp_port)
      self._probe_hub.start()

  def apply_config(self, raw_config: dict) -> None:
    """Hot-reload obstacle_nav settings."""
    self._settings = ObstacleNavSettings(raw_config)
    self._wizard.apply_settings(self._settings)
    self._detector.apply_settings(self._settings)

  def close(self) -> None:
    """Stop the TCP probe hub."""
    if self._probe_hub is not None:
      self._probe_hub.stop()
      self._probe_hub = None

  @property
  def settings(self) -> ObstacleNavSettings:
    """Return current settings."""
    return self._settings

  @property
  def calib_panel(self) -> ImuCalibPanel:
    """Return the full-screen calib panel."""
    return self._calib_panel

  @property
  def stuck_panel(self) -> StuckOverlayPanel:
    """Return the stuck overlay panel."""
    return self._stuck_panel

  def nav_roi_layout(self) -> NavRoiLayout:
    """Return ROI layout for HUD guides and future depth/OF crops."""
    return NavRoiLayout(self._settings)

  def draw_roi_guides(self, frame) -> None:
    """Paint ground / obstacle split lines when enabled."""
    if not self._settings.enabled or not self._settings.show_roi_guides:
      return
    self._roi_guide_panel.draw(frame, self.nav_roi_layout())

  def is_calib_open(self) -> bool:
    """True while the IMU wizard owns the HUD."""
    return self._settings.enabled and self._wizard.is_active()

  def blocks_teleop(self) -> bool:
    """True when sticks must not drive (wizard active)."""
    return self.is_calib_open()

  def calib_snapshot(self) -> ImuCalibSnapshot:
    """Return the current wizard HUD snapshot."""
    return self._wizard.snapshot()

  def stuck_report(self) -> StuckReport:
    """Return the last stuck report (for tests / HUD)."""
    return self._report

  def stuck_probe(self) -> StuckProbe:
    """Return live analyzer probe for TCP / SSH."""
    return self._detector.probe(ready=self._ready_for_stuck)

  def show_stuck_overlay(self) -> bool:
    """True when the top-down stuck card should paint."""
    if not self._settings.stuck_detection_enabled:
      return False
    return self._overlay_visible

  def should_cut_drive(self) -> bool:
    """True when attitude tip must stop motors (other stuck = HUD only)."""
    if not self._settings.stuck_detection_enabled:
      return False
    return self._report.cuts_drive()

  def chassis_frame(self) -> ImuChassisFrame:
    """Return the active IMU chassis frame."""
    return self._detector.frame()

  def on_disconnect(self) -> None:
    """Tear down wizard and stuck state when the pad drops."""
    self._wizard.reset()
    self._detector.reset()
    self._report = StuckReport.clear()
    self._overlay_visible = False
    self._clear_since_ms = None
    self._ready_for_stuck = False

  def begin_calib_after_checklist(self) -> None:
    """Start the wizard after the peripheral checklist is dismissed."""
    if not self._settings.enabled or not self._settings.calib_after_connect:
      self._ready_for_stuck = True
      self._detector.set_frame(ImuChassisFrame.default())
      return
    self._wizard.start(time.ticks_ms())
    self._ready_for_stuck = False

  def confirm_modal(self) -> bool:
    """Handle A / OK on the calib wizard. Return True if consumed."""
    if not self.is_calib_open():
      return False
    snap = self._wizard.snapshot()
    now = time.ticks_ms()
    if snap.step == ImuCalibStep.INTRO and snap.can_confirm:
      self._wizard.confirm(now)
      return True
    if snap.step == ImuCalibStep.DONE and snap.can_confirm:
      self._wizard.confirm(now)
      self._detector.set_frame(self._wizard.frame())
      self._ready_for_stuck = True
      print("obstacle: stuck armed after calib DONE")
      return True
    return False

  def skip_calib(self) -> bool:
    """Skip wizard and enable stuck detection with defaults."""
    if not self._settings.enabled or not self._settings.calib_skippable:
      return False
    step = self._wizard.snapshot().step
    if step in (ImuCalibStep.IDLE, ImuCalibStep.DONE, ImuCalibStep.SKIPPED):
      return False
    self._wizard.skip()
    self._detector.set_frame(self._wizard.frame())
    self._ready_for_stuck = True
    self._wizard.reset()
    print("obstacle: stuck armed after calib skip")
    return True

  def note_drive_command(self, drive: DriveOutput) -> None:
    """Remember last teleop axes for stuck analysis."""
    self._last_cmd = drive

  def tick(
    self,
    *,
    imu: YahboomImuAttitude | None,
    accel: YahboomImuAccel | None,
    encoders: EncoderCounts,
  ) -> DriveOutput | None:
    """Advance calib / stuck. Return drive override during wizard, else None."""
    if not self._settings.enabled:
      return None
    now = time.ticks_ms()
    pitch = imu.pitch_deg if imu is not None else 0.0
    roll = imu.roll_deg if imu is not None else 0.0
    yaw = imu.yaw_deg if imu is not None else 0.0
    ax = accel.ax if accel is not None else 0.0
    ay = accel.ay if accel is not None else 0.0
    az = accel.az if accel is not None else 9.8
    accel_valid = accel is not None

    if (
      not self._ready_for_stuck
      and self._wizard.snapshot().step == ImuCalibStep.DONE
    ):
      self._detector.set_frame(self._wizard.frame())
      self._ready_for_stuck = True
      print("obstacle: stuck armed at calib DONE")

    if self._wizard.is_active():
      override = self._wizard.tick(
        now,
        pitch_deg=pitch,
        roll_deg=roll,
        yaw_deg=yaw,
        ax=ax,
        ay=ay,
        az=az,
      )
      if self._wizard.snapshot().step == ImuCalibStep.DONE:
        return DriveOutput()
      if self._wizard.snapshot().step == ImuCalibStep.SKIPPED:
        self._detector.set_frame(self._wizard.frame())
        self._ready_for_stuck = True
        self._wizard.reset()
        return None
      return override if override is not None else DriveOutput()

    if self._ready_for_stuck and self._settings.stuck_detection_enabled:
      sample = MotionProbeSample(
        timestamp_ms=now,
        pitch_deg=pitch,
        roll_deg=roll,
        yaw_deg=yaw,
        ax=ax,
        ay=ay,
        az=az,
        encoder_sum=encoders.m1 + encoders.m2 + encoders.m3 + encoders.m4,
        axis_forward=self._last_cmd.axis_forward,
        axis_spin=self._last_cmd.axis_spin,
        axis_strafe=self._last_cmd.axis_strafe,
        accel_valid=accel_valid,
      )
      prev = self._report.level
      self._report = self._detector.update(sample)
      if self._report.level != StuckLevel.OK and self._report.level != prev:
        print(
          f"obstacle: {self._report.level.value}"
          f" side={self._report.side.value}"
          f" {self._report.detail}"
          f" cmd_f={self._last_cmd.axis_forward}"
          f" cmd_s={self._last_cmd.axis_strafe}"
          f" a=({ax:.2f},{ay:.2f},{az:.2f})"
          f" enc={sample.encoder_sum}"
        )
      self._maybe_log_probe(now)
      self._update_overlay_visibility(now)
      if self.should_cut_drive():
        return DriveOutput()
    return None

  def _maybe_log_probe(self, now_ms: int) -> None:
    driving = (
      abs(self._last_cmd.axis_forward) > self._settings.cmd_axis_threshold
      or abs(self._last_cmd.axis_strafe) > self._settings.cmd_axis_threshold
      or abs(self._last_cmd.axis_spin) > self._settings.cmd_axis_threshold
      or self._report.level != StuckLevel.OK
    )
    if not driving:
      return
    if now_ms - self._last_probe_log_ms < self._settings.probe_log_ms:
      return
    self._last_probe_log_ms = now_ms
    line = self.stuck_probe().log_line()
    if self._probe_hub is not None:
      self._probe_hub.publish(line)
    else:
      print(f"obstacle probe: {line}")

  def _update_overlay_visibility(self, now_ms: int) -> None:
    if self._report.level != StuckLevel.OK:
      self._overlay_visible = True
      self._clear_since_ms = None
      return
    if not self._overlay_visible:
      return
    if self._clear_since_ms is None:
      self._clear_since_ms = now_ms
      return
    if now_ms - self._clear_since_ms >= self._settings.overlay_clear_ms:
      self._overlay_visible = False
      self._clear_since_ms = None
