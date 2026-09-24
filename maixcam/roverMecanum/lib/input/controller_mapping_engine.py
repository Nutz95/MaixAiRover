"""Map Xbox controller state into DriveOutput using config.json rules."""

from lib.input.axis_curve import apply_curve
from lib.input.axis_source import AxisSource
from lib.input.controller_button import ControllerButton
from lib.input.dpad_direction import DpadDirection
from lib.input.drive_action import DriveAction
from lib.input.drive_action_catalog import DriveActionCatalog
from lib.input.drive_output import DriveOutput
from lib.config.rover_config import RoverConfig


class ControllerMappingEngine:
  """Apply config mapping: sticks, triggers, d-pad -> rover drive axes."""

  def __init__(self, config: dict) -> None:
    self._actions = DriveActionCatalog()
    self._forward_src = AxisSource.LEFT_Y
    self._strafe_src = AxisSource.TRIGGER_DIFF
    self._spin_src = AxisSource.RIGHT_X
    self._pivot_src = AxisSource.LEFT_X
    self._invert = set()
    self._dpad = {}
    self._buttons = {}
    self._deadzone_percent = 0
    self._sensitivity = 0.7
    self._expo = 2.2
    self._curve = "log"
    self.update_config(config)

  def update_config(self, config: dict) -> None:
    """Parse config.json strings into enums once; runtime uses enums only."""
    mapping = config.get("mapping", {}) if isinstance(config.get("mapping"), dict) else {}
    axes_map = mapping.get("axes", {}) if isinstance(mapping.get("axes"), dict) else {}
    invert = mapping.get("invert", {}) if isinstance(mapping.get("invert"), dict) else {}
    dpad_map = mapping.get("dpad", {}) if isinstance(mapping.get("dpad"), dict) else {}
    buttons = mapping.get("buttons", {}) if isinstance(mapping.get("buttons"), dict) else {}
    rover = RoverConfig.from_mapping(
      config.get("rover", {}) if isinstance(config.get("rover"), dict) else {},
    )

    self._forward_src = AxisSource.from_config(
      axes_map.get("drive_forward"), AxisSource.LEFT_Y,
    )
    self._strafe_src = AxisSource.from_config(
      axes_map.get("drive_strafe"), AxisSource.TRIGGER_DIFF,
    )
    spin_raw = axes_map.get("drive_spin", axes_map.get("drive_rotate"))
    self._spin_src = AxisSource.from_config(spin_raw, AxisSource.RIGHT_X)
    self._pivot_src = AxisSource.from_config(
      axes_map.get("drive_pivot"), AxisSource.LEFT_X,
    )

    self._invert = set()
    for key, enabled in invert.items():
      source = AxisSource.from_config(key)
      if source is not None and enabled:
        self._invert.add(source)

    self._dpad = {}
    for direction in DpadDirection:
      action = DriveAction.from_config(dpad_map.get(direction.value))
      if action is not None:
        self._dpad[direction] = action

    self._buttons = {}
    for key, action_name in buttons.items():
      button = ControllerButton.from_config(key)
      action = DriveAction.from_config(action_name)
      if button is not None and action is not None:
        self._buttons[button] = action

    self._deadzone_percent = rover.deadzone_percent
    self._sensitivity = rover.axis_sensitivity_percent / 100.0
    self._expo = rover.axis_expo
    self._curve = rover.axis_curve

  def compute(self, state) -> DriveOutput:
    """Build DriveOutput from a ControllerState snapshot."""
    out = DriveOutput()
    deadzone = int(32768 * self._deadzone_percent / 100)

    dpad = self._dpad_axes(state)
    if dpad is not None:
      out.axis_strafe = self._shape_axis(dpad.strafe, deadzone)
      out.axis_forward = self._shape_axis(dpad.forward, deadzone)
      out.preset_action = self._button_preset(state)
      return out

    forward = self._apply_invert(self._source_value(state, self._forward_src), self._forward_src)
    strafe = self._apply_invert(self._source_value(state, self._strafe_src), self._strafe_src)
    spin = self._apply_invert(self._source_value(state, self._spin_src), self._spin_src)
    pivot = self._apply_invert(self._source_value(state, self._pivot_src), self._pivot_src)

    out.axis_forward = self._shape_axis(forward, deadzone)
    out.axis_strafe = self._shape_axis(strafe, deadzone)
    out.axis_spin = self._shape_axis(spin, deadzone)
    out.axis_pivot = self._shape_axis(pivot, deadzone)
    out.preset_action = self._button_preset(state)
    return out

  def _source_value(self, state, source: AxisSource) -> int:
    if source is AxisSource.LEFT_X:
      return state.left_x
    if source is AxisSource.LEFT_Y:
      return state.left_y
    if source is AxisSource.RIGHT_X:
      return state.right_x
    if source is AxisSource.RIGHT_Y:
      return state.right_y
    if source is AxisSource.LT:
      return state.lt
    if source is AxisSource.RT:
      return state.rt
    if source is AxisSource.TRIGGER_DIFF:
      return state.trigger_diff()
    return 0

  def _apply_invert(self, value: int, source: AxisSource) -> int:
    return -value if source in self._invert else value

  def _apply_deadzone(self, value: int, deadzone: int) -> int:
    if abs(value) <= deadzone:
      return 0
    sign = 1 if value > 0 else -1
    mag = abs(value) - deadzone
    span = max(1, 32767 - deadzone)
    return sign * min(32767, int(mag * 32767 / span))

  def _shape_axis(self, value: int, deadzone: int) -> int:
    """Deadzone, response curve, then sensitivity scale."""
    value = self._apply_deadzone(value, deadzone)
    if value == 0:
      return 0
    sign = 1 if value > 0 else -1
    norm = min(1.0, abs(value) / 32767.0)
    norm = apply_curve(norm, self._curve, self._expo)
    norm = min(1.0, norm * self._sensitivity)
    return sign * int(norm * 32767)

  def _dpad_axes(self, state):
    if not self._dpad:
      return None
    dx = state.dpad_x
    dy = state.dpad_y
    if dx == 0 and dy == 0:
      return None
    direction = None
    if dy < 0 and dx < 0:
      direction = DpadDirection.UP_LEFT
    elif dy < 0 and dx > 0:
      direction = DpadDirection.UP_RIGHT
    elif dy > 0 and dx < 0:
      direction = DpadDirection.DOWN_LEFT
    elif dy > 0 and dx > 0:
      direction = DpadDirection.DOWN_RIGHT
    elif dy < 0:
      direction = DpadDirection.UP
    elif dy > 0:
      direction = DpadDirection.DOWN
    elif dx < 0:
      direction = DpadDirection.LEFT
    elif dx > 0:
      direction = DpadDirection.RIGHT
    if direction is None:
      return None
    action = self._dpad.get(direction)
    if action is None:
      return None
    return self._actions.axes_for_action(action)

  def _button_preset(self, state):
    for button, action in self._buttons.items():
      if not state.take_edge(button):
        continue
      if self._actions.get(action) is not None:
        return action
    return None
