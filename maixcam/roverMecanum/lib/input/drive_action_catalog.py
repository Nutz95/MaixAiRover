"""Catalog of named drive actions (d-pad presets and button stops)."""

from typing import Dict, Optional

from lib.input.axis_pair import AxisPair
from lib.input.drive_action import DriveAction
from lib.input.drive_action_spec import DriveActionSpec
from lib.input.evdev_constants import AXIS_MAX


class DriveActionCatalog:
  """Lookup table for mapped DriveAction values."""

  def __init__(self) -> None:
    self._actions: Dict[DriveAction, DriveActionSpec] = {
      DriveAction.STOP: DriveActionSpec(action=DriveAction.STOP, is_stop=True),
      DriveAction.FORWARD: DriveActionSpec(action=DriveAction.FORWARD, forward=-AXIS_MAX),
      DriveAction.BACKWARD: DriveActionSpec(action=DriveAction.BACKWARD, forward=AXIS_MAX),
      DriveAction.STRAFE_LEFT: DriveActionSpec(action=DriveAction.STRAFE_LEFT, strafe=-AXIS_MAX),
      DriveAction.STRAFE_RIGHT: DriveActionSpec(action=DriveAction.STRAFE_RIGHT, strafe=AXIS_MAX),
      DriveAction.DIAG_FL: DriveActionSpec(
        action=DriveAction.DIAG_FL, strafe=-AXIS_MAX, forward=-AXIS_MAX,
      ),
      DriveAction.DIAG_FR: DriveActionSpec(
        action=DriveAction.DIAG_FR, strafe=AXIS_MAX, forward=-AXIS_MAX,
      ),
      DriveAction.DIAG_BL: DriveActionSpec(
        action=DriveAction.DIAG_BL, strafe=-AXIS_MAX, forward=AXIS_MAX,
      ),
      DriveAction.DIAG_BR: DriveActionSpec(
        action=DriveAction.DIAG_BR, strafe=AXIS_MAX, forward=AXIS_MAX,
      ),
      DriveAction.SPIN_LEFT: DriveActionSpec(action=DriveAction.SPIN_LEFT, spin=-AXIS_MAX),
      DriveAction.SPIN_RIGHT: DriveActionSpec(action=DriveAction.SPIN_RIGHT, spin=AXIS_MAX),
      DriveAction.PIVOT_RIGHT: DriveActionSpec(action=DriveAction.PIVOT_RIGHT, pivot=AXIS_MAX),
      DriveAction.PIVOT_REAR: DriveActionSpec(action=DriveAction.PIVOT_REAR, pivot=-AXIS_MAX),
    }

  def get(self, action: DriveAction) -> Optional[DriveActionSpec]:
    """Return the action spec for a DriveAction, or None if unknown."""
    if not isinstance(action, DriveAction):
      return None
    return self._actions.get(action)

  def axes_for_action(self, action: DriveAction) -> Optional[AxisPair]:
    """Return strafe/forward axes for a d-pad style action."""
    spec = self.get(action)
    if spec is None:
      return None
    return AxisPair(strafe=spec.strafe, forward=spec.forward)
