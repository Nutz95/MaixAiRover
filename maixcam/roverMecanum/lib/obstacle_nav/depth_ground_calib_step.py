"""Named steps for post-IMU depth ground-split calibration."""

from enum import Enum


class DepthGroundCalibStep(Enum):
  """Ground-split wizard progression."""

  IDLE = "idle"
  WAIT_DEPTH = "wait_depth"
  PROPOSE = "propose"
  DONE = "done"
  SKIPPED = "skipped"
