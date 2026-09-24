"""Drive arbitration: ball-follow vs manual sticks (Yahboom/ESP)."""

from __future__ import annotations

from lib.ball_follow.ball_follow_controller import BallFollowController
from lib.input.drive_output import DriveOutput
from lib.motion.encoder_counts import EncoderCounts
from lib.motion.encoder_odometry import EncoderOdometry
from lib.motion.rover_motion_client import RoverMotionClient


class DriveDispatcher:
  """Keep mode arbitration out of the raw motion send path."""

  def __init__(
    self,
    rover: RoverMotionClient,
    ball_follow: BallFollowController,
    get_frame,
    *,
    odometry: EncoderOdometry | None = None,
    get_yaw_deg=None,
    get_encoders=None,
  ) -> None:
    """Wire rover, ball controller, optional yaw/encoders, and a frame getter."""
    self._rover = rover
    self._ball_follow = ball_follow
    self._get_frame = get_frame
    self._odometry = odometry
    self._get_yaw_deg = get_yaw_deg
    self._get_encoders = get_encoders
    self._prev_encoders: EncoderCounts | None = None

  def dispatch(self, drive: DriveOutput, manual_resume_pending: bool) -> bool:
    """Apply one teleop tick; return updated ``manual_resume_pending``."""
    if self._ball_follow.enabled:
      frame = self._get_frame()
      yaw_deg = self._get_yaw_deg() if self._get_yaw_deg is not None else None
      encoder_delta_deg = self._encoder_yaw_delta_deg()
      command = self._ball_follow.update(
        frame, yaw_deg=yaw_deg, encoder_yaw_delta_deg=encoder_delta_deg,
      )
      self._rover.send_joystick(0, command.forward, command.spin, 0)
      return manual_resume_pending

    self._prev_encoders = None
    if manual_resume_pending:
      self._rover.send_stop()
      return False

    if drive.preset_action is not None:
      self._rover.send_preset(drive.preset_action)
      return False
    if drive.is_idle():
      self._rover.send_stop()
      return False
    self._rover.send_joystick(
      drive.axis_strafe,
      drive.axis_forward,
      drive.axis_spin,
      drive.axis_pivot,
    )
    return False

  def _encoder_yaw_delta_deg(self) -> float | None:
    if self._get_encoders is None or self._odometry is None:
      return None
    try:
      counts = self._get_encoders()
    except Exception as enc_error:
      print(f"drive: encoders: {enc_error}")
      return None
    if self._prev_encoders is None:
      self._prev_encoders = counts
      return 0.0
    delta = EncoderCounts(
      m1=counts.m1 - self._prev_encoders.m1,
      m2=counts.m2 - self._prev_encoders.m2,
      m3=counts.m3 - self._prev_encoders.m3,
      m4=counts.m4 - self._prev_encoders.m4,
    )
    self._prev_encoders = counts
    return self._odometry.yaw_degrees_from_delta(delta)
