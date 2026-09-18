"""Mecanum kinematics mixer from stick axes to wheel setpoints."""

from lib.drive_command import DriveCommand
from lib.wheel_speeds import WheelSpeeds


class MecanumMixer:
  """Convert strafe/forward/spin/pivot axes into four wheel setpoints."""

  AXIS_MAX = 32768

  def __init__(self, max_setpoint: int = 50) -> None:
    self._max_setpoint = max(1, int(max_setpoint))

  def mix(self, command: DriveCommand) -> WheelSpeeds:
    """Mix a DriveCommand into signed wheel setpoints in ±max_setpoint."""
    strafe = self._normalize(command.axis_strafe)
    forward = self._normalize(-command.axis_forward)
    spin = self._normalize(command.axis_spin)
    pivot = self._normalize(command.axis_pivot)

    if strafe == 0 and forward == 0 and spin == 0 and pivot == 0:
      return WheelSpeeds()

    upper_left = forward + strafe + spin
    upper_right = forward - strafe - spin
    lower_left = forward - strafe + spin
    lower_right = forward + strafe - spin

    if pivot > 0:
      upper_left += pivot
      lower_left += pivot
      upper_right = (upper_right * (self.AXIS_MAX - pivot)) // self.AXIS_MAX
      lower_right = (lower_right * (self.AXIS_MAX - pivot)) // self.AXIS_MAX
    elif pivot < 0:
      magnitude = -pivot
      upper_right += magnitude
      lower_right += magnitude
      upper_left = (upper_left * (self.AXIS_MAX - magnitude)) // self.AXIS_MAX
      lower_left = (lower_left * (self.AXIS_MAX - magnitude)) // self.AXIS_MAX

    max_magnitude = max(
      abs(upper_left),
      abs(upper_right),
      abs(lower_left),
      abs(lower_right),
    )
    if max_magnitude == 0:
      return WheelSpeeds()

    input_magnitude = max(abs(strafe), abs(forward), abs(spin), abs(pivot))
    session = max(0, min(255, int(command.max_speed)))
    effective = (self._max_setpoint * session * input_magnitude) // (255 * self.AXIS_MAX)
    if effective == 0 and input_magnitude > 0:
      effective = 1

    return WheelSpeeds(
      front_left=self._scale(upper_left, effective, max_magnitude),
      front_right=self._scale(upper_right, effective, max_magnitude),
      rear_left=self._scale(lower_left, effective, max_magnitude),
      rear_right=self._scale(lower_right, effective, max_magnitude),
    )

  def _normalize(self, axis: int) -> int:
    value = max(-self.AXIS_MAX, min(self.AXIS_MAX - 1, int(axis)))
    return value

  def _scale(self, component: int, effective: int, max_magnitude: int) -> int:
    scaled = (component * effective) // max_magnitude
    return max(-self._max_setpoint, min(self._max_setpoint, int(scaled)))
