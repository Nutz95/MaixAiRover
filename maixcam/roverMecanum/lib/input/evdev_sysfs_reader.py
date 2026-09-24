import os

from lib.input.abs_range import AbsRange
from lib.input.evdev_constants import ABS_BRAKE, ABS_GAS, ABS_RX, ABS_RY, ABS_RZ, ABS_X, ABS_Y, ABS_Z, default_abs_range

# Linux input subsystem ABS_* names for sysfs paths.
_ABS_LINUX_NAMES = {
  ABS_X: "x",
  ABS_Y: "y",
  ABS_Z: "z",
  ABS_RX: "rx",
  ABS_RY: "ry",
  ABS_RZ: "rz",
  ABS_GAS: "gas",
  ABS_BRAKE: "brake",
}


class EvdevSysfsReader:
  """Read /sys/class/input metadata for evdev devices."""

  def read_field(self, event_path, field):
    """Read one sysfs text field under the input device root."""
    for root in self._device_roots(event_path):
      path = f"{root}/{field}"
      try:
        with open(path, "r") as f:
          return f.read().strip()
      except OSError as field_error:
        print(f"evdev sysfs: {path}: {field_error}")
    return ""

  def read_name(self, event_path):
    """Return the kernel input device name."""
    return self.read_field(event_path, "name")

  def read_vendor(self, event_path):
    """Return the USB/Bluetooth vendor id string."""
    return self.read_field(event_path, "id/vendor")

  def read_absinfo_real(self, event_path, axis_code):
    """Return AbsRange for an ABS axis from sysfs, or None."""
    for root in self._device_roots(event_path):
      for rel in (f"absinfo/{axis_code}", f"absinfo/{axis_code:02x}"):
        try:
          min_v = int(self._read_text(f"{root}/{rel}/min"))
          max_v = int(self._read_text(f"{root}/{rel}/max"))
          flat = int(self._read_text(f"{root}/{rel}/flat"))
          return AbsRange(minimum=min_v, maximum=max_v, flat=flat)
        except (OSError, ValueError) as abs_error:
          print(f"evdev sysfs absinfo: {abs_error}")
    return None

  def read_abs_value(self, event_path, axis_code):
    """Read the kernel's current axis value (fallback when ioctl unavailable)."""
    name = _ABS_LINUX_NAMES.get(axis_code)
    for root in self._device_roots(event_path):
      rels = [
        f"abs/{axis_code:02x}/value",
        f"abs/{axis_code}/value",
        f"absinfo/{axis_code}/value",
        f"absinfo/{axis_code:02x}/value",
      ]
      if name:
        rels.extend([f"abs/ABS_{name.upper()}/value", f"abs/{name}/value"])
      for rel in rels:
        try:
          return int(self._read_text(f"{root}/{rel}"))
        except (OSError, ValueError) as value_error:
          print(f"evdev sysfs abs value: {value_error}")
    return None

  def read_abs_capabilities(self, event_path):
    """Return the ABS capability bitmask from sysfs, or 0."""
    text = self.read_field(event_path, "capabilities/abs")
    if not text:
      return 0
    try:
      return int(text, 16)
    except ValueError:
      return 0

  def _device_roots(self, event_path):
    base = os.path.basename(event_path)
    roots = []
    seen = set()

    def add(path):
      if path and path not in seen:
        seen.add(path)
        roots.append(path)

    add(f"/sys/class/input/{base}/device")
    try:
      add(os.path.realpath(f"/sys/class/input/{base}/device"))
    except OSError as realpath_error:
      print(f"evdev sysfs realpath: {realpath_error}")
    return roots

  def _read_text(self, path):
    with open(path, "r") as f:
      return f.read().strip()
