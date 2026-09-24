"""Logical Xbox face / bumper buttons used after config parse."""

from enum import Enum


class ControllerButton(Enum):
  """Controller buttons referenced by config.json and the HUD."""

  A = "btn_a"
  B = "btn_b"
  X = "btn_x"
  Y = "btn_y"
  LB = "btn_lb"
  RB = "btn_rb"
  LT = "btn_lt"
  RT = "btn_rt"
  SELECT = "btn_select"
  START = "btn_start"

  @classmethod
  def from_config(cls, value):
    """Parse a config button key into ControllerButton, or None."""
    if not isinstance(value, str) or not value.strip():
      return None
    try:
      return cls(value.strip().lower())
    except ValueError:
      return None
