"""Avoidance HUD / drive hint from depth bands."""

from enum import Enum


class AvoidanceHint(Enum):
  """Coarse dodge suggestion for HUD arrow and soft drive override."""

  NONE = "none"
  STRAFE_LEFT = "strafe_left"
  STRAFE_RIGHT = "strafe_right"
  REVERSE = "reverse"
  STOP_FORWARD = "stop_forward"
