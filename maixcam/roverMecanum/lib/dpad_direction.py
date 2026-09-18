"""D-pad direction keys used in mapping config."""

from enum import Enum


class DpadDirection(Enum):
  """Eight-way d-pad slots from config.json mapping.dpad."""

  UP = "up"
  DOWN = "down"
  LEFT = "left"
  RIGHT = "right"
  UP_LEFT = "up_left"
  UP_RIGHT = "up_right"
  DOWN_LEFT = "down_left"
  DOWN_RIGHT = "down_right"
