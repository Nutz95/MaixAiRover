"""Catalog of named drive actions (d-pad presets and button stops)."""

from typing import Dict, Optional

from lib.axis_pair import AxisPair
from lib.drive_action import DriveAction
from lib.drive_action_spec import DriveActionSpec


class DriveActionCatalog:
  """Lookup table for mapped DriveAction values."""

  def __init__(self) -> None:
    self._actions: Dict[DriveAction, DriveActionSpec] = {
      DriveAction.STOP: DriveActionSpec(action=DriveAction.STOP, is_stop=True),
      DriveAction.FORWARD: DriveActionSpec(action=DriveAction.FORWARD, forward=-32767),
      DriveAction.BACKWARD: DriveActionSpec(action=DriveAction.BACKWARD, forward=32767),
      DriveAction.STRAFE_LEFT: DriveActionSpec(action=DriveAction.STRAFE_LEFT, strafe=-32767),
      DriveAction.STRAFE_RIGHT: DriveActionSpec(action=DriveAction.STRAFE_RIGHT, strafe=32767),
      DriveAction.DIAG_FL: DriveActionSpec(
        action=DriveAction.DIAG_FL, strafe=-32767, forward=-32767,
      ),
      DriveAction.DIAG_FR: DriveActionSpec(
        action=DriveAction.DIAG_FR, strafe=32767, forward=-32767,
      ),
      DriveAction.DIAG_BL: DriveActionSpec(
        action=DriveAction.DIAG_BL, strafe=-32767, forward=32767,
      ),
      DriveAction.DIAG_BR: DriveActionSpec(
        action=DriveAction.DIAG_BR, strafe=32767, forward=32767,
      ),
      DriveAction.SPIN_LEFT: DriveActionSpec(action=DriveAction.SPIN_LEFT, spin=-32767),
      DriveAction.SPIN_RIGHT: DriveActionSpec(action=DriveAction.SPIN_RIGHT, spin=32767),
      DriveAction.PIVOT_RIGHT: DriveActionSpec(action=DriveAction.PIVOT_RIGHT, pivot=32767),
      DriveAction.PIVOT_REAR: DriveActionSpec(action=DriveAction.PIVOT_REAR, pivot=-32767),
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
