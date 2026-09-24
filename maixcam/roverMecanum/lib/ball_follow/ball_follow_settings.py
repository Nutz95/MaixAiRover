"""Typed ball detection and follow tuning from config.json."""

from lib.config.config_parse_helpers import as_bool, as_float, as_int, as_str, section

_DEFAULT_GREEN = [[40, 90, -90, -40, 25, 75]]
_DEFAULT_RED = [[0, 80, 40, 80, 10, 80]]
_COLOR_ORDER = ("green", "red")


class BallFollowSettings:
  """Calibration and safety limits for the ball-follow controller."""

  __slots__ = (
    "default_color",
    "color_presets",
    "area_threshold",
    "pixels_threshold",
    "min_blob_width",
    "min_blob_height",
    "min_aspect_ratio",
    "max_aspect_ratio",
    "image_center_x_ratio",
    "target_height_ratio",
    "target_tolerance_ratio",
    "too_close_height_ratio",
    "too_close_center_y_ratio",
    "min_distance_error",
    "exit_velocity_threshold",
    "velocity_timeout_ms",
    "spin_gain",
    "spin_damping",
    "forward_gain",
    "min_spin_axis",
    "max_spin_axis",
    "min_forward_axis",
    "max_forward_axis",
    "max_retreat_axis",
    "search_spin_axis",
    "search_turn_ms",
    "search_turn_deg",
    "search_pause_ms",
    "search_retreat_ms",
    "search_retreat_axis",
    "compass_fix_spin_axis",
    "compass_fix_tolerance_deg",
    "compass_fix_timeout_ms",
    "horizontal_deadzone",
    "lost_search_ms",
    "trajectory_max_points",
    "forward_axis_sign",
    "spin_axis_sign",
    "depth_fusion_enabled",
    "depth_model_path",
    "depth_interval_ms",
    "depth_near_ratio",
    "depth_roi_top_ratio",
    "depth_roi_bottom_ratio",
    "depth_roi_left_ratio",
    "depth_roi_right_ratio",
  )

  def __init__(self, raw: dict):
    """Parse and bound the ball-follow section at the config boundary."""
    follow = section(raw, "ball_follow")
    self.color_presets = self._read_color_presets(follow)
    self.default_color = self._read_default_color(follow)
    self.area_threshold = max(1, as_int(follow, "area_threshold", 120))
    self.pixels_threshold = max(1, as_int(follow, "pixels_threshold", 120))
    self.min_blob_width = max(1, as_int(follow, "min_blob_width", 8))
    self.min_blob_height = max(1, as_int(follow, "min_blob_height", 8))
    self.min_aspect_ratio = max(0.1, as_float(follow, "min_aspect_ratio", 0.55))
    self.max_aspect_ratio = min(4.0, as_float(follow, "max_aspect_ratio", 1.8))
    self.image_center_x_ratio = self._ratio(follow, "image_center_x_ratio", 0.5)
    self.target_height_ratio = self._ratio(follow, "target_height_ratio", 0.22)
    self.target_tolerance_ratio = self._ratio(
      follow, "target_tolerance_ratio", 0.07,
    )
    self.too_close_height_ratio = self._ratio(
      follow, "too_close_height_ratio", 0.40,
    )
    self.too_close_center_y_ratio = self._ratio(
      follow, "too_close_center_y_ratio", 0.72,
    )
    self.min_distance_error = self._ratio(follow, "min_distance_error", 0.04)
    self.exit_velocity_threshold = max(
      0.0, as_float(follow, "exit_velocity_threshold", 0.05),
    )
    self.velocity_timeout_ms = max(
      100, as_int(follow, "velocity_timeout_ms", 1000),
    )
    self.spin_gain = max(1.0, as_float(follow, "spin_gain", 14000.0))
    self.spin_damping = max(0.0, as_float(follow, "spin_damping", 2800.0))
    self.forward_gain = max(1.0, as_float(follow, "forward_gain", 30000.0))
    self.max_spin_axis = max(1, min(32767, as_int(follow, "max_spin_axis", 9000)))
    self.min_spin_axis = max(
      1, min(self.max_spin_axis, as_int(follow, "min_spin_axis", 6500)),
    )
    self.max_forward_axis = max(
      1, min(32767, as_int(follow, "max_forward_axis", 15000)),
    )
    self.min_forward_axis = max(
      1, min(self.max_forward_axis, as_int(follow, "min_forward_axis", 7000)),
    )
    self.max_retreat_axis = max(
      1, min(self.max_forward_axis, as_int(follow, "max_retreat_axis", 6500)),
    )
    self.search_spin_axis = max(
      1, min(32767, as_int(follow, "search_spin_axis", 8000)),
    )
    self.search_turn_ms = max(500, as_int(follow, "search_turn_ms", 2200))
    self.search_turn_deg = max(0.0, min(720.0, as_float(follow, "search_turn_deg", 360.0)))
    self.search_pause_ms = max(0, as_int(follow, "search_pause_ms", 800))
    self.search_retreat_ms = max(200, as_int(follow, "search_retreat_ms", 700))
    self.search_retreat_axis = max(
      1, min(self.max_retreat_axis, as_int(follow, "search_retreat_axis", 4500)),
    )
    self.compass_fix_spin_axis = max(
      1, min(32767, as_int(follow, "compass_fix_spin_axis", 5000)),
    )
    self.compass_fix_tolerance_deg = max(
      1.0, min(45.0, as_float(follow, "compass_fix_tolerance_deg", 8.0)),
    )
    self.compass_fix_timeout_ms = max(
      200, as_int(follow, "compass_fix_timeout_ms", 2500),
    )
    self.horizontal_deadzone = self._ratio(follow, "horizontal_deadzone", 0.15)
    self.lost_search_ms = max(500, as_int(follow, "lost_search_ms", 2000))
    self.trajectory_max_points = max(
      4, min(64, as_int(follow, "trajectory_max_points", 24)),
    )
    # Yahboom +vx is forward on positive axis_forward (Keyestudio UART used -1).
    self.forward_axis_sign = self._axis_sign(follow, "forward_axis_sign", 1)
    self.spin_axis_sign = self._axis_sign(follow, "spin_axis_sign", 1)
    self.depth_fusion_enabled = as_bool(follow, "depth_fusion_enabled", False)
    self.depth_model_path = as_str(
      follow, "depth_model_path", "/root/models/depth_anything_v2_vits.mud",
    )
    self.depth_interval_ms = max(50, as_int(follow, "depth_interval_ms", 150))
    self.depth_near_ratio = self._ratio(follow, "depth_near_ratio", 0.35)
    self.depth_roi_top_ratio = self._ratio(follow, "depth_roi_top_ratio", 0.35)
    self.depth_roi_bottom_ratio = self._ratio(follow, "depth_roi_bottom_ratio", 0.85)
    self.depth_roi_left_ratio = self._ratio(follow, "depth_roi_left_ratio", 0.25)
    self.depth_roi_right_ratio = self._ratio(follow, "depth_roi_right_ratio", 0.75)

  @property
  def thresholds(self) -> list:
    """Return LAB thresholds for the configured default color."""
    return self.thresholds_for(self.default_color)

  def thresholds_for(self, color: str) -> list:
    """Return LAB thresholds for one named color preset."""
    key = color if color in self.color_presets else self.default_color
    return self.color_presets[key]

  def next_color(self, color: str) -> str:
    """Return the next color name in the green/red cycle."""
    if color not in _COLOR_ORDER:
      return self.default_color
    index = _COLOR_ORDER.index(color)
    return _COLOR_ORDER[(index + 1) % len(_COLOR_ORDER)]

  @staticmethod
  def _ratio(block: dict, key: str, default: float) -> float:
    """Read a normalized setting and keep it between zero and one."""
    return max(0.0, min(1.0, as_float(block, key, default)))

  @staticmethod
  def _axis_sign(block: dict, key: str, default: int) -> int:
    """Read an axis sign and normalize every non-negative value to one."""
    return -1 if as_int(block, key, default) < 0 else 1

  def _read_default_color(self, block: dict) -> str:
    """Read the startup color and fall back to green."""
    color = as_str(block, "color", "green").strip().lower()
    return color if color in self.color_presets else "green"

  @staticmethod
  def _read_color_presets(block: dict) -> dict:
    """Read green/red LAB presets; keep the legacy thresholds key as green."""
    colors = block.get("colors")
    presets = {
      "green": list(_DEFAULT_GREEN),
      "red": list(_DEFAULT_RED),
    }
    if isinstance(colors, dict):
      for name in _COLOR_ORDER:
        parsed = BallFollowSettings._read_thresholds(colors, name, presets[name])
        presets[name] = parsed
    elif "thresholds" in block:
      presets["green"] = BallFollowSettings._read_thresholds(
        block, "thresholds", _DEFAULT_GREEN,
      )
    return presets

  @staticmethod
  def _read_thresholds(block: dict, key: str, default: list) -> list:
    """Read six-value LAB thresholds as ints for MaixPy find_blobs."""
    value = block.get(key, default)
    if not isinstance(value, list) or not value:
      return [list(row) for row in default]
    thresholds = []
    for candidate in value:
      if not isinstance(candidate, list) or len(candidate) != 6:
        continue
      try:
        thresholds.append([int(round(float(item))) for item in candidate])
      except (TypeError, ValueError) as threshold_error:
        print(f"ball config: invalid LAB threshold ignored: {threshold_error}")
    return thresholds or [list(row) for row in default]
