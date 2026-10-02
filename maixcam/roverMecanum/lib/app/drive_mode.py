"""Teleop / avoid / ball-follow operating modes."""

from __future__ import annotations

from enum import Enum


class DriveMode(Enum):
  """Cycled with Xbox SELECT: fluid manual → depth avoid → ball follow."""

  MANUAL = "manual"
  AVOID = "avoid"
  FOLLOW = "follow"

  def next_mode(self) -> DriveMode:
    """Return the next mode in the SELECT cycle."""
    order = (DriveMode.MANUAL, DriveMode.AVOID, DriveMode.FOLLOW)
    return order[(order.index(self) + 1) % len(order)]

  def uses_depth(self) -> bool:
    """True when DepthAnything should run for obstacles / ball band."""
    return self is not DriveMode.MANUAL

  def uses_avoidance(self) -> bool:
    """True when soft obstacle override is allowed."""
    return self is not DriveMode.MANUAL

  def uses_ball_follow(self) -> bool:
    """True when automatic ball track drives the chassis."""
    return self is DriveMode.FOLLOW
