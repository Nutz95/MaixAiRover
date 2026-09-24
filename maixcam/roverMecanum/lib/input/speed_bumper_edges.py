"""LB/RB speed-adjust edge flags."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeedBumperEdges:
  """One-shot bumper press edges for session max-speed changes."""

  left_bumper: bool = False
  right_bumper: bool = False
