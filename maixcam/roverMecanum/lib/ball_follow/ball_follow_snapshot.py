"""Typed ball-follow state exposed to the HUD."""

from dataclasses import dataclass
from typing import Optional

from lib.ball_follow.ball_follow_command import BallFollowCommand
from lib.ball_follow.ball_observation import BallObservation


@dataclass(frozen=True)
class BallFollowSnapshot:
  """Mode, latest observation, and latest safe automatic command."""

  enabled: bool
  color: str
  observation: Optional[BallObservation]
  trajectory: list
  command: BallFollowCommand

  @property
  def mode_label(self) -> str:
    """Return the short HUD label for the active control mode."""
    if not self.enabled:
      return "MANUAL"
    return f"BALL {self.color.upper()}"
