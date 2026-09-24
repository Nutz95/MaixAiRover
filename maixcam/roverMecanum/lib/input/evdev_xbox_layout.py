from lib.input.evdev_constants import (
  ABS_BRAKE, ABS_GAS, ABS_RX, ABS_RY, ABS_RZ, ABS_X, ABS_Y, ABS_Z,
  XBOX_VENDOR_ID,
)


class XboxAxisLayout:
  """Xbox evdev axis roles (USB/BT/kernel layouts differ on MaixCam)."""

  def __init__(self, left_x, left_y, right_x, right_y, lt, rt):
    self.left_x = left_x
    self.left_y = left_y
    self.right_x = right_x
    self.right_y = right_y
    self.lt = lt
    self.rt = rt

  @classmethod
  def detect(cls, sysfs, event_path, evdev_cfg=None):
    """Choose ABS codes for sticks/triggers from config or auto-detect."""
    evdev_cfg = evdev_cfg or {}
    if cls._has_explicit_codes(evdev_cfg):
      layout = cls(
        int(evdev_cfg["left_x"]),
        int(evdev_cfg["left_y"]),
        int(evdev_cfg["right_x"]),
        int(evdev_cfg["right_y"]),
        int(evdev_cfg["lt"]),
        int(evdev_cfg["rt"]),
      )
      cls._log_layout(layout, "config")
      return layout

    profile = evdev_cfg.get("layout", "auto")
    if profile == "standard":
      layout = cls(ABS_X, ABS_Y, ABS_RX, ABS_RY, ABS_Z, ABS_RZ)
      cls._log_layout(layout, "standard")
      return layout
    if profile == "maixcam_bt":
      layout = cls(ABS_X, ABS_Y, ABS_Z, ABS_RZ, ABS_BRAKE, ABS_GAS)
      cls._log_layout(layout, "maixcam_bt")
      return layout

    return cls._auto_detect(sysfs, event_path)

  @classmethod
  def _auto_detect(cls, sysfs, event_path):
    caps = sysfs.read_abs_capabilities(event_path)
    vendor = sysfs.read_vendor(event_path)

    lt, rt = cls._pick_triggers(sysfs, event_path, caps)
    right_x, right_y = cls._pick_right_stick(sysfs, event_path, caps, lt, rt)

    if vendor == XBOX_VENDOR_ID and caps == 0:
      layout = cls(ABS_X, ABS_Y, ABS_Z, ABS_RZ, ABS_BRAKE, ABS_GAS)
      cls._log_layout(layout, "auto/xbox-no-caps")
      return layout

    layout = cls(ABS_X, ABS_Y, right_x, right_y, lt, rt)
    cls._log_layout(layout, f"auto/caps=0x{caps:x}" if caps else "auto")
    return layout

  @classmethod
  def _pick_triggers(cls, sysfs, event_path, caps):
    if caps:
      if caps & (1 << ABS_GAS) and caps & (1 << ABS_BRAKE):
        return ABS_BRAKE, ABS_GAS
      z_info = sysfs.read_absinfo_real(event_path, ABS_Z)
      if z_info and cls._is_trigger_range(z_info):
        return ABS_Z, ABS_RZ

    z_info = sysfs.read_absinfo_real(event_path, ABS_Z)
    rz_info = sysfs.read_absinfo_real(event_path, ABS_RZ)
    if z_info and rz_info and cls._is_trigger_range(z_info):
      if cls._is_trigger_range(rz_info):
        return ABS_Z, ABS_RZ

    gas_info = sysfs.read_absinfo_real(event_path, ABS_GAS)
    brake_info = sysfs.read_absinfo_real(event_path, ABS_BRAKE)
    if gas_info or brake_info:
      return ABS_BRAKE, ABS_GAS

    return ABS_BRAKE, ABS_GAS

  @classmethod
  def _pick_right_stick(cls, sysfs, event_path, caps, lt, rt):
    trigger_set = {lt, rt}
    if caps and (caps & (1 << ABS_RX)) and (caps & (1 << ABS_RY)):
      if ABS_RX not in trigger_set and ABS_RY not in trigger_set:
        return ABS_RX, ABS_RY

    z_info = sysfs.read_absinfo_real(event_path, ABS_Z)
    if z_info and not cls._is_trigger_range(z_info):
      rz_info = sysfs.read_absinfo_real(event_path, ABS_RZ)
      if rz_info and not cls._is_trigger_range(rz_info):
        return ABS_Z, ABS_RZ

    return ABS_Z, ABS_RZ

  @staticmethod
  def _has_explicit_codes(evdev_cfg):
    keys = ("left_x", "left_y", "right_x", "right_y", "lt", "rt")
    return all(k in evdev_cfg for k in keys)

  @staticmethod
  def _is_trigger_range(axis_range):
    min_v = axis_range.minimum
    max_v = axis_range.maximum
    span = max_v - min_v
    if min_v >= 0 and span <= 1024:
      return True
    return min_v >= 0 and max_v <= 255

  @staticmethod
  def _log_layout(layout, source):
    print(
      f"xbox layout ({source}):"
      f" L=({layout.left_x},{layout.left_y})"
      f" R=({layout.right_x},{layout.right_y})"
      f" T=({layout.lt},{layout.rt})"
    )
