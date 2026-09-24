"""Typed drive-axis output after controller mapping."""

from dataclasses import dataclass
from typing import Optional

from lib.input.drive_action import DriveAction


@dataclass
class DriveOutput:
  """Mapped stick/trigger values ready for the motion layer."""

  axis_strafe: int = 0
  axis_forward: int = 0
  axis_spin: int = 0
  axis_pivot: int = 0
  preset_action: Optional[DriveAction] = None

  def is_idle(self, threshold: int = 250) -> bool:
    """Return True when all drive axes are near zero."""
    return (
      abs(self.axis_strafe) <= threshold
      and abs(self.axis_forward) <= threshold
      and abs(self.axis_spin) <= threshold
      and abs(self.axis_pivot) <= threshold
    )
