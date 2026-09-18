"""Named teleop / preset drive actions (config string -> enum at the boundary)."""

from enum import Enum


class DriveAction(Enum):
  """Drive presets referenced by d-pad and face-button mapping."""

  STOP = "stop"
  FORWARD = "forward"
  BACKWARD = "backward"
  STRAFE_LEFT = "strafe_left"
  STRAFE_RIGHT = "strafe_right"
  DIAG_FL = "diag_fl"
  DIAG_FR = "diag_fr"
  DIAG_BL = "diag_bl"
  DIAG_BR = "diag_br"
  SPIN_LEFT = "spin_left"
  SPIN_RIGHT = "spin_right"
  PIVOT_RIGHT = "pivot_right"
  PIVOT_REAR = "pivot_rear"

  @classmethod
  def from_config(cls, value):
    """Parse a config.json action string into DriveAction, or None."""
    if not isinstance(value, str) or not value.strip():
      return None
    try:
      return cls(value.strip().lower())
    except ValueError:
      return None
