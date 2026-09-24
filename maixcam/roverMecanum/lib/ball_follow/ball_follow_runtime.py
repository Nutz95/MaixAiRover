"""Ball-follow + depth HUD wiring used by XboxRoverApp."""

from __future__ import annotations

from lib.ball_follow.ball_follow_controller import BallFollowController
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.drive_dispatcher import DriveDispatcher
from lib.config.motor_config import MotorConfig
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

  def toggle_mode(self) -> None:
    """Toggle automatic mode and stop motors once."""
    enabled = not self.controller.enabled
    self.controller.set_enabled(enabled)
    try:
      self._rover.send_stop()
    except Exception as stop_error:
      print(f"ball: stop on toggle: {stop_error}")
    self.manual_resume_pending = not enabled
    print(f"ball: {'enabled' if enabled else 'disabled'}")

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
    """Force manual mode (shutdown path)."""
    self.controller.set_enabled(False)

  def dispatch(self, drive) -> None:
    """Apply one teleop tick through the ball/manual arbitrator."""
    self.manual_resume_pending = self._drive.dispatch(
      drive, self.manual_resume_pending,
    )

  def snapshot(self):
    """Return the HUD snapshot for overlays."""
    return self.controller.snapshot()

  def draw_depth(self, frame) -> None:
    """Optional DepthAnything fusion (visual only)."""
    self.depth_hud.draw(frame, self.controller.snapshot())

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
