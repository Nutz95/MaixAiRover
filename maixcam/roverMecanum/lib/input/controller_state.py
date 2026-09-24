"""Current Xbox controller axes and button latch state."""

from lib.input.controller_button import ControllerButton


class ControllerState:
  """Normalized stick/trigger axes plus button press edges."""

  def __init__(self):
    self.left_x = 0
    self.left_y = 0
    self.right_x = 0
    self.right_y = 0
    self.lt = 0
    self.rt = 0
    self.dpad_x = 0
    self.dpad_y = 0
    self.buttons = {}
    self.pressed_edge = {}

  def trigger_diff(self):
    """Return RT minus LT on the shared stick scale."""
    return int(self.rt) - int(self.lt)

  def set_button(self, button: ControllerButton, pressed: bool):
    """Update a button and latch a rising-edge flag."""
    was = self.buttons.get(button, False)
    self.buttons[button] = pressed
    if pressed and not was:
      self.pressed_edge[button] = True

  def consume_edges(self):
    """Return and clear every latched press edge."""
    edges = dict(self.pressed_edge)
    self.pressed_edge.clear()
    return edges

  def take_edge(self, button: ControllerButton):
    """Return True once per button press (does not clear other edges)."""
    if self.pressed_edge.get(button):
      self.pressed_edge.pop(button, None)
      return True
    return False

  def copy(self):
    """Return a deep-enough clone for the UI / mapping snapshot."""
    clone = ControllerState()
    clone.left_x = self.left_x
    clone.left_y = self.left_y
    clone.right_x = self.right_x
    clone.right_y = self.right_y
    clone.lt = self.lt
    clone.rt = self.rt
    clone.dpad_x = self.dpad_x
    clone.dpad_y = self.dpad_y
    clone.buttons = dict(self.buttons)
    clone.pressed_edge = dict(self.pressed_edge)
    return clone
