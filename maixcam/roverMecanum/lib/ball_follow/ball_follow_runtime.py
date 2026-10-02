"""Ball-follow + depth HUD wiring used by XboxRoverApp."""

from __future__ import annotations

from lib.app.drive_mode import DriveMode
from lib.ball_follow.ball_follow_controller import BallFollowController
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_follow_snapshot import BallFollowSnapshot
from lib.ball_follow.drive_dispatcher import DriveDispatcher
from lib.config.motor_config import MotorConfig
from lib.input.drive_output import DriveOutput
from lib.motion.encoder_odometry import EncoderOdometry
from lib.motion.rover_motion_client import RoverMotionClient
from lib.vision.depth_fusion_hud import DepthFusionHud


class BallFollowRuntime:
  """Own controller, depth HUD, and drive arbitration for vision mode."""

  def __init__(
    self,
    config: dict,
    rover: RoverMotionClient,
    motor_cfg: MotorConfig,
    *,
    yahboom_board=None,
    get_frame=None,
  ) -> None:
    """Build policy + dispatcher bound to the live camera/Yahboom sensors."""
    self._yahboom_board = yahboom_board
    self._get_frame = get_frame
    self._rover = rover
    self.settings = BallFollowSettings(config)
    self.controller = BallFollowController(self.settings)
    self.depth_hud = DepthFusionHud(self.settings)
    self.manual_resume_pending = False
    self._drive_mode = DriveMode.MANUAL
    self._drive = DriveDispatcher(
      rover=rover,
      ball_follow=self.controller,
      get_frame=self._frame,
      odometry=EncoderOdometry(motor_cfg),
      get_yaw_deg=self._yaw_deg,
      get_encoders=self._read_encoders,
    )

  def apply_config(self, config: dict) -> None:
    """Reload ball-follow + depth settings after config.json changes."""
    settings = BallFollowSettings(config)
    self.controller.apply_settings(settings)
    self.depth_hud.apply_settings(settings)
    self.settings = settings

  def drive_mode(self) -> DriveMode:
    """Return MANUAL / AVOID / FOLLOW."""
    return self._drive_mode

  def toggle_mode(self) -> DriveMode:
    """Cycle SELECT: MANUAL → AVOID → FOLLOW → MANUAL. Stop motors once."""
    self._drive_mode = self._drive_mode.next_mode()
    self.controller.set_enabled(self._drive_mode.uses_ball_follow())
    try:
      self._rover.send_stop()
    except Exception as stop_error:
      print(f"drive mode: stop on toggle: {stop_error}")
    self.manual_resume_pending = not self._drive_mode.uses_ball_follow()
    print(f"drive mode: {self._drive_mode.value}")
    return self._drive_mode

  def cycle_color(self) -> None:
    """Cycle green/red LAB presets."""
    color = self.controller.cycle_color()
    if self.controller.enabled:
      try:
        self._rover.send_stop()
      except Exception as stop_error:
        print(f"ball: stop on color: {stop_error}")
    print(f"ball: color={color}")

  def disable(self) -> None:
    """Force MANUAL (shutdown path)."""
    self._drive_mode = DriveMode.MANUAL
    self.controller.set_enabled(False)

  def set_blend_drive(self, blend_drive) -> None:
    """Attach soft avoidance blender used in FOLLOW dispatch."""
    self._drive.set_blend_drive(blend_drive)

  def dispatch(self, drive: DriveOutput) -> None:
    """Apply one teleop tick through the ball/manual arbitrator."""
    self.manual_resume_pending = self._drive.dispatch(
      drive, self.manual_resume_pending,
    )

  def snapshot(self) -> BallFollowSnapshot:
    """Return the HUD snapshot including SELECT drive mode."""
    snap = self.controller.snapshot()
    return BallFollowSnapshot(
      enabled=snap.enabled,
      color=snap.color,
      observation=snap.observation,
      trajectory=snap.trajectory,
      command=snap.command,
      target_center_x_ratio=snap.target_center_x_ratio,
      target_center_y_ratio=snap.target_center_y_ratio,
      drive_mode=self._drive_mode,
    )

  def draw_depth(
    self,
    frame,
    nav_roi=None,
    *,
    force_depth_paint: bool = False,
    enabled: bool | None = None,
  ) -> None:
    """Paint depth HUD only — never gates ball detect/track/drive.

    Ball position + follow run on the teleop tick (``dispatch`` → detector).
    Depth busy means the last distance band stays stale; tracking continues.
    Default ``enabled`` follows the drive mode (off in MANUAL).
    """
    depth_on = self._drive_mode.uses_depth() if enabled is None else enabled
    try:
      self.depth_hud.draw(
        frame,
        self.snapshot(),
        nav_roi=nav_roi,
        force_depth_paint=force_depth_paint,
        enabled=depth_on,
      )
    except MemoryError as oom:
      print(f"ball: depth draw OOM (ignored): {oom}")
    except Exception as depth_error:
      print(f"ball: depth draw: {depth_error}")

  def last_depth_image(self):
    """Return last DepthAnything plane for obstacle bands, or None."""
    return self.depth_hud.last_depth_image()

  def _frame(self):
    if self._get_frame is None:
      return None
    return self._get_frame()

  def _yaw_deg(self):
    if self._yahboom_board is None:
      return None
    attitude = self._yahboom_board.imu_attitude()
    if attitude is None:
      return None
    return attitude.yaw_deg

  def _read_encoders(self):
    if self._yahboom_board is not None:
      self._yahboom_board.poll()
      return self._yahboom_board.read_encoders()
    return self._rover.read_encoders()
