"""Named steps for the post-connect IMU calibration wizard."""

from enum import Enum


class ImuCalibStep(Enum):
  """Wizard progression for rest bias and axis sign learning."""

  IDLE = "idle"
  INTRO = "intro"
  REST = "rest"
  FORWARD = "forward"
  REVERSE = "reverse"
  SPIN_CW = "spin_cw"
  SPIN_CCW = "spin_ccw"
  DONE = "done"
  SKIPPED = "skipped"
