"""Map teleop DriveCommand axes onto Yahboom chassis velocity limits."""

from __future__ import annotations

from lib.motion.chassis_velocity import ChassisVelocity
from lib.motion.drive_command import DriveCommand
from lib.yahboom.yahboom_config import YahboomConfig

_AXIS_MAX = 32767.0


class DriveCommandChassisMapper:
  """Scale stick axes + session max_speed into ``ChassisVelocity``."""

  def __init__(self, config: YahboomConfig) -> None:
    self._config = config

  def map_command(self, command: DriveCommand) -> ChassisVelocity:
    """Convert a teleop command into body-frame velocity for the STM32 PID.

    Yahboom Rosmaster frame (ROS-style): +vx forward, +vy left, +vz CCW.
    Teleop ``axis_strafe`` / spin use + = right / CW, so vy and vz are negated.
    """
    session = max(0.0, min(1.0, float(command.max_speed) / 255.0))
    vx = (float(command.axis_forward) / _AXIS_MAX) * self._config.max_vx * session
    # +axis_strafe = crab right → Yahboom wants negative vy.
    vy = -(float(command.axis_strafe) / _AXIS_MAX) * self._config.max_vy * session
    # Pivot shares yaw with spin (mecanum body rotate).
    yaw_axis = float(command.axis_spin) + float(command.axis_pivot)
    yaw_axis = max(-_AXIS_MAX, min(_AXIS_MAX, yaw_axis))
    # +spin (stick right) = CW → Yahboom wants negative vz.
    vz = -(yaw_axis / _AXIS_MAX) * self._config.max_vz * session
    return ChassisVelocity(vx=vx, vy=vy, vz=vz)
