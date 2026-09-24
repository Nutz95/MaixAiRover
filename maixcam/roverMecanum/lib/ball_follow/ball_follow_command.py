"""Typed forward/spin command produced by the ball-follow policy."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BallFollowCommand:
  """Sequential ball-follow command in the existing signed axis space."""

  forward: int = 0
  spin: int = 0
  reason: str = "stop"
