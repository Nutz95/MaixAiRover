"""Logical stick / trigger sources used by the mapping engine."""

from enum import Enum


class AxisSource(Enum):
  """Controller axis roles after config.json is parsed."""

  LEFT_X = "left_x"
  LEFT_Y = "left_y"
  RIGHT_X = "right_x"
  RIGHT_Y = "right_y"
  LT = "lt"
  RT = "rt"
  TRIGGER_DIFF = "trigger_diff"

  @classmethod
  def from_config(cls, value, default=None):
    """Parse a config axis name; return default when missing/invalid."""
    if not isinstance(value, str) or not value.strip():
      return default
    try:
      return cls(value.strip().lower())
    except ValueError:
      return default
