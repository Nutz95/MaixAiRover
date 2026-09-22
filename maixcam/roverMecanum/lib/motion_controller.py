"""High-level motion API: continuous drive and encoder-based turns."""

import time
from typing import Optional

from lib.drive_action import DriveAction
from lib.drive_action_catalog import DriveActionCatalog
from lib.drive_command import DriveCommand
from lib.encoder_counts import EncoderCounts
from lib.encoder_odometry import EncoderOdometry
from lib.mecanum_mixer import MecanumMixer
from lib.motor_config import MotorConfig
from lib.wheel_speeds import WheelSpeeds


class MotionController:
  """Orchestrate mixer + wheel drive port for teleop and relative yaw turns."""

  def __init__(
    self,
    driver,
    mixer: MecanumMixer,
    odometry: EncoderOdometry,
    motor_config: MotorConfig,
    actions: Optional[DriveActionCatalog] = None,
  ) -> None:
    self._driver = driver
    self._mixer = mixer
    self._odometry = odometry
    self._motor_config = motor_config
    self._actions = actions if actions is not None else DriveActionCatalog()
    self._last_speeds = WheelSpeeds()
    self._max_speed = 255

  def initialize(self, settle_s: float = 0.0) -> None:
    """Initialize the underlying motor driver."""
    self._driver.initialize(settle_s=settle_s)
    try:
      self.stop()
    except OSError:
      pass

  def set_max_speed(self, speed: int) -> None:
    """Set the session max-speed scaler used by teleop (0..255)."""
    self._max_speed = max(0, min(255, int(speed)))

  def last_wheel_speeds(self) -> WheelSpeeds:
    """Return the last commanded wheel setpoints (for HUD / tests)."""
    return self._last_speeds

  def drive(self, command: DriveCommand) -> WheelSpeeds:
    """Mix and send a continuous teleop command."""
    scaled = DriveCommand(
      axis_strafe=command.axis_strafe,
      axis_forward=command.axis_forward,
      axis_spin=command.axis_spin,
      axis_pivot=command.axis_pivot,
      max_speed=command.max_speed if command.max_speed else self._max_speed,
    )
    speeds = self._mixer.mix(scaled)
    self._driver.set_wheel_speeds(speeds)
    self._last_speeds = speeds
    return speeds

  def apply_preset(self, action: DriveAction) -> WheelSpeeds:
    """Apply a DriveAction preset at the current session max speed."""
    spec = self._actions.get(action)
    if spec is None or spec.is_stop:
      return self.stop()
    return self.drive(
      DriveCommand(
        axis_strafe=spec.strafe,
        axis_forward=spec.forward,
        axis_spin=spec.spin,
        axis_pivot=spec.pivot,
        max_speed=self._max_speed,
      )
    )

  def jog_wheel(self, wheel: str, sign: int) -> WheelSpeeds:
    """Run one named wheel (FL/FR/RL/RR) at max_setpoint; others stay at 0."""
    mag = max(1, int(self._motor_config.max_setpoint))
    value = mag if int(sign) >= 0 else -mag
    speeds = WheelSpeeds(
      front_left=value if wheel == "FL" else 0,
      front_right=value if wheel == "FR" else 0,
      rear_left=value if wheel == "RL" else 0,
      rear_right=value if wheel == "RR" else 0,
    )
    self._driver.set_wheel_speeds(speeds)
    self._last_speeds = speeds
    return speeds

  def stop(self) -> WheelSpeeds:
    """Stop all motors and clear last setpoints."""
    self._driver.stop()
    self._last_speeds = WheelSpeeds()
    return self._last_speeds

  def turn_degrees(
    self,
    angle_deg: float,
    speed: Optional[int] = None,
    timeout_s: float = 8.0,
    poll_s: float = 0.02,
  ) -> bool:
    """Spin in place until estimated yaw reaches ``angle_deg`` or timeout."""
    if abs(angle_deg) < 0.5:
      self.stop()
      return True
    setpoint = speed if speed is not None else max(10, self._motor_config.max_setpoint // 2)
    setpoint = max(1, min(self._motor_config.max_setpoint, int(setpoint)))
    target_pulses = self._odometry.pulses_for_yaw_degrees(angle_deg)
    self._driver.clear_encoders()
    sign = 1 if angle_deg > 0 else -1
    self._driver.set_wheel_speeds(
      WheelSpeeds(
        front_left=sign * setpoint,
        front_right=-sign * setpoint,
        rear_left=sign * setpoint,
        rear_right=-sign * setpoint,
      )
    )
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
      counts = self._driver.read_encoders()
      progressed = self._progress_pulses(counts, sign)
      if progressed >= target_pulses:
        self.stop()
        return True
      time.sleep(poll_s)
    self.stop()
    return False

  def _progress_pulses(self, counts: EncoderCounts, sign: int) -> int:
    left = (counts.m1 + counts.m3) / 2.0
    right = (counts.m2 + counts.m4) / 2.0
    delta = (left - right) / 2.0
    if sign < 0:
      delta = -delta
    return int(max(0.0, delta))
