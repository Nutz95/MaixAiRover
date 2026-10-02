"""Typed ball-follow state exposed to the HUD."""

from dataclasses import dataclass
from typing import Optional

from lib.app.drive_mode import DriveMode
from lib.ball_follow.ball_follow_command import BallFollowCommand
from lib.ball_follow.ball_observation import BallObservation


@dataclass(frozen=True)
class BallFollowSnapshot:
  """Mode, latest observation, and latest safe automatic command."""

  enabled: bool
  color: str
  observation: Optional[BallObservation]
  trajectory: list[BallObservation]
  command: BallFollowCommand
  target_center_x_ratio: float = 0.5
  target_center_y_ratio: float = 0.50
  drive_mode: DriveMode = DriveMode.MANUAL

  @property
  def mode_label(self) -> str:
    """Return the short HUD label for the active control mode."""
    if self.drive_mode is DriveMode.MANUAL:
      return "MODE MANUAL"
    if self.drive_mode is DriveMode.AVOID:
      return "MODE AVOID"
    return f"FOLLOW {self.color.upper()}"
