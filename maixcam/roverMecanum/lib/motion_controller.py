"""High-level motion API: continuous drive and encoder-based turns."""

import time
from typing import Optional

from lib.chassis_motion_port import ChassisMotionPort
from lib.drive_action import DriveAction
from lib.drive_action_catalog import DriveActionCatalog
from lib.drive_command import DriveCommand
from lib.drive_command_chassis_mapper import DriveCommandChassisMapper
from lib.encoder_counts import EncoderCounts
from lib.encoder_odometry import EncoderOdometry
from lib.mecanum_mixer import MecanumMixer
from lib.motor_config import MotorConfig
from lib.wheel_drive_port import WheelDrivePort
from lib.wheel_speeds import WheelSpeeds


class MotionController:
  """Orchestrate teleop via wheel PWM port (ESP) or chassis velocity (Yahboom)."""

  def __init__(
    self,
    mixer: MecanumMixer,
    odometry: EncoderOdometry,
    motor_config: MotorConfig,
    *,
    wheel_driver: WheelDrivePort | None = None,
    chassis_driver: ChassisMotionPort | None = None,
    chassis_mapper: DriveCommandChassisMapper | None = None,
    actions: Optional[DriveActionCatalog] = None,
  ) -> None:
    if (wheel_driver is None) == (chassis_driver is None):
      raise ValueError("provide exactly one of wheel_driver or chassis_driver")
    if chassis_driver is not None and chassis_mapper is None:
      raise ValueError("chassis_mapper required with chassis_driver")
    self._wheel = wheel_driver
    self._chassis = chassis_driver
    self._chassis_mapper = chassis_mapper
    self._mixer = mixer
    self._odometry = odometry
    self._motor_config = motor_config
    self._actions = actions if actions is not None else DriveActionCatalog()
    self._last_speeds = WheelSpeeds()
    self._max_speed = 255

  def initialize(self, settle_s: float = 0.0) -> None:
    """Initialize the underlying motor driver."""
    if self._wheel is not None:
      self._wheel.initialize(settle_s=settle_s)
    else:
      assert self._chassis is not None
      self._chassis.initialize(settle_s=settle_s)
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
    """Mix/send a continuous teleop command (wheels or chassis velocity)."""
    scaled = DriveCommand(
      axis_strafe=command.axis_strafe,
      axis_forward=command.axis_forward,
      axis_spin=command.axis_spin,
      axis_pivot=command.axis_pivot,
      max_speed=command.max_speed if command.max_speed else self._max_speed,
    )
    if self._chassis is not None and self._chassis_mapper is not None:
      velocity = self._chassis_mapper.map_command(scaled)
      self._chassis.set_velocity(velocity)
      # HUD: mirror axes as pseudo wheel setpoints (not PWM).
      self._last_speeds = WheelSpeeds(
        front_left=int(scaled.axis_forward + scaled.axis_strafe + scaled.axis_spin) // 4,
        front_right=int(scaled.axis_forward - scaled.axis_strafe - scaled.axis_spin) // 4,
        rear_left=int(scaled.axis_forward - scaled.axis_strafe + scaled.axis_spin) // 4,
        rear_right=int(scaled.axis_forward + scaled.axis_strafe - scaled.axis_spin) // 4,
      )
      return self._last_speeds
    assert self._wheel is not None
    speeds = self._mixer.mix(scaled)
    self._wheel.set_wheel_speeds(speeds)
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
    if self._wheel is None:
      raise OSError("jog_wheel requires a wheel drive backend")
    mag = max(1, int(self._motor_config.max_setpoint))
    value = mag if int(sign) >= 0 else -mag
    speeds = WheelSpeeds(
      front_left=value if wheel == "FL" else 0,
      front_right=value if wheel == "FR" else 0,
      rear_left=value if wheel == "RL" else 0,
      rear_right=value if wheel == "RR" else 0,
    )
    self._wheel.set_wheel_speeds(speeds)
    self._last_speeds = speeds
    return speeds

  def stop(self) -> WheelSpeeds:
    """Stop all motors and clear last setpoints."""
    if self._wheel is not None:
      self._wheel.stop()
    else:
      assert self._chassis is not None
      self._chassis.stop()
    self._last_speeds = WheelSpeeds()
    return self._last_speeds

  def turn_degrees(
    self,
    angle_deg: float,
    setpoint: Optional[int] = None,
    timeout_s: float = 6.0,
    poll_s: float = 0.02,
  ) -> bool:
    """Spin in place until estimated yaw reaches ``angle_deg`` or timeout."""
    if self._wheel is None:
      raise OSError("turn_degrees requires wheel encoders on a wheel backend")
    if setpoint is None:
      setpoint = max(1, int(self._motor_config.max_setpoint))
    target_pulses = self._odometry.pulses_for_yaw_degrees(angle_deg)
    sign = 1 if angle_deg >= 0 else -1
    self._wheel.clear_encoders()
    start = time.time()
    while time.time() - start < timeout_s:
      self._wheel.set_wheel_speeds(
        WheelSpeeds(
          front_left=sign * setpoint,
          front_right=-sign * setpoint,
          rear_left=sign * setpoint,
          rear_right=-sign * setpoint,
        )
      )
      counts = self._wheel.read_encoders()
      delta = EncoderCounts(
        m1=counts.m1,
        m2=counts.m2,
        m3=counts.m3,
        m4=counts.m4,
      )
      if abs(self._odometry.yaw_degrees_from_delta(delta)) >= abs(angle_deg):
        self.stop()
        return True
      if abs(counts.m1) + abs(counts.m2) >= abs(target_pulses) * 2:
        self.stop()
        return True
      time.sleep(poll_s)
    self.stop()
    return False
