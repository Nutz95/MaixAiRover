"""Coarse contact side relative to the rover chassis."""

from enum import Enum


class CollisionSide(Enum):
  """Which edge of the rover likely hit an obstacle."""

  NONE = "none"
  FRONT = "front"
  REAR = "rear"
  LEFT = "left"
  RIGHT = "right"
  UNKNOWN = "unknown"
