"""App-facing motion client used by XboxRoverApp (replaces UART client)."""

from lib.battery_reading import BatteryReading
from lib.drive_action import DriveAction
from lib.drive_command import DriveCommand
from lib.motion_controller import MotionController
from lib.wheel_speeds import WheelSpeeds


class RoverMotionClient:
  """Thin adapter exposing joystick/preset/stop APIs for the app loop."""

  def __init__(self, motion: MotionController, is_stub: bool = True) -> None:
    self._motion = motion
    self._is_stub = bool(is_stub)
    self._max_speed = 255
    self._i2c_error = ""
    self._battery = None

  def is_stub(self) -> bool:
    """True when motion uses the in-process stub (not live ESP UART)."""
    return self._is_stub

  def note_i2c_error(self, message: str) -> None:
    """Record the last I2C failure for HUD / logs."""
    self._i2c_error = message

  def last_i2c_error(self) -> str:
    """Return the last I2C failure message, or empty if the bus is healthy."""
    return self._i2c_error

  def set_battery(self, reading: BatteryReading) -> None:
    """Store the last ADC_BAT reading from the motor driver."""
    self._battery = reading

  def last_battery(self):
    """Return the last battery reading, or None if ADC_BAT was never read."""
    return self._battery

  def set_max_speed(self, speed: int) -> None:
    """Update session max-speed (0..255) used by subsequent commands."""
    self._max_speed = max(0, min(255, int(speed)))
    self._motion.set_max_speed(self._max_speed)

  def send_joystick(
    self,
    axis_strafe: int,
    axis_forward: int,
    axis_spin: int = 0,
    axis_pivot: int = 0,
  ) -> WheelSpeeds:
    """Send a continuous four-axis teleop command."""
    return self._motion.drive(
      DriveCommand(
        axis_strafe=int(axis_strafe),
        axis_forward=int(axis_forward),
        axis_spin=int(axis_spin),
        axis_pivot=int(axis_pivot),
        max_speed=self._max_speed,
      )
    )

  def send_preset(self, action: DriveAction) -> WheelSpeeds:
    """Send a DriveAction preset (for example STOP or FORWARD)."""
    return self._motion.apply_preset(action)

  def send_stop(self) -> WheelSpeeds:
    """Stop all motors."""
    return self._motion.stop()

  def last_wheel_speeds(self) -> WheelSpeeds:
    """Return last commanded wheel setpoints for HUD display."""
    return self._motion.last_wheel_speeds()
