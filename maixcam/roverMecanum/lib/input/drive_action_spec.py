"""Named drive action with optional strafe/forward axis targets."""

from dataclasses import dataclass

from lib.input.drive_action import DriveAction


@dataclass(frozen=True)
class DriveActionSpec:
  """One named teleop/preset action used by d-pad and button mapping."""

  action: DriveAction
  strafe: int = 0
  forward: int = 0
  spin: int = 0
  pivot: int = 0
  is_stop: bool = False
