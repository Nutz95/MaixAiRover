"""Map a centered ABS stick axis to signed -32768..32767."""

from lib.input.evdev_constants import AXIS_MAX


class EvdevAxisMapper:
  """Map a centered ABS axis to signed -32768..32767."""

  def __init__(self, min_v, max_v, flat):
    self.min_v = min_v
    self.max_v = max_v
    self.flat = flat
    self.raw = (min_v + max_v) // 2

  def set_raw(self, value):
    """Store the latest raw ABS value from the kernel."""
    self.raw = int(value)

  def to_axis(self):
    """Return the normalized stick axis on ±AXIS_MAX."""
    center = (self.min_v + self.max_v) // 2
    half = max(1, (self.max_v - self.min_v) // 2)
    delta = self.raw - center
    if abs(delta) <= self.flat:
      return 0
    sign = 1 if delta > 0 else -1
    mag = abs(delta) - self.flat
    span = max(1, half - self.flat)
    scaled = min(AXIS_MAX, int(mag * AXIS_MAX / span))
    return sign * scaled
