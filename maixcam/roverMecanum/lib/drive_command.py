"""Continuous teleop command for the motion controller."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DriveCommand:
  """Four-axis teleop command on the ±32767 stick scale."""

  axis_strafe: int = 0
  axis_forward: int = 0
  axis_spin: int = 0
  axis_pivot: int = 0
  max_speed: int = 255
