"""Typed ball detection and follow tuning from config.json."""

from __future__ import annotations

from lib.ball_follow.ball_color_preset import BallColorPreset
from lib.ball_follow.color_name_cycle import ColorNameCycle
from lib.ball_follow.lab_threshold import LabThreshold
from lib.ball_follow.lab_threshold_set import LabThresholdSet
from lib.config.config_parse_helpers import as_bool, as_float, as_int, as_str, as_str_list, section
from lib.input.evdev_constants import AXIS_MAX
from lib.vision.depth_view_mode import DepthViewMode


class BallFollowSettings:
  """Calibration and safety limits for the ball-follow controller."""

  __slots__ = (
    "default_color",
    "color_cycle",
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
    "ball_diameter_cm",
    "depth_fusion_enabled",
    "depth_model_path",
    "depth_interval_ms",
    "depth_view",
    "depth_rgb_alpha",
    "depth_show_contours",
    "depth_contour_low",
    "depth_contour_high",
    "depth_contour_alpha",
    "depth_contour_thickness",
    "depth_ball_band_enabled",
    "depth_close_warmth",
    "depth_far_warmth",
    "depth_close_cm",
    "depth_far_cm",
    "depth_near_ratio",
    "depth_roi_top_ratio",
    "depth_roi_bottom_ratio",
    "depth_roi_left_ratio",
    "depth_roi_right_ratio",
  )

  def __init__(self, raw: dict) -> None:
    """Parse and bound the ball-follow section at the config boundary."""
    follow = section(raw, "ball_follow")
    self.color_presets = self._read_color_presets(follow)
    self.color_cycle = self._read_color_cycle(follow, self.color_presets)
    self.default_color = self._read_default_color(follow)
    self.area_threshold = max(1, as_int(follow, "area_threshold", 120))
    self.pixels_threshold = max(1, as_int(follow, "pixels_threshold", 120))
    self.min_blob_width = max(1, as_int(follow, "min_blob_width", 8))
    self.min_blob_height = max(1, as_int(follow, "min_blob_height", 8))
    self.min_aspect_ratio = max(0.1, as_float(follow, "min_aspect_ratio", 0.55))
    self.max_aspect_ratio = min(4.0, as_float(follow, "max_aspect_ratio", 1.8))
    self.image_center_x_ratio = self._ratio(follow, "image_center_x_ratio", 0.5)
    self.target_height_ratio = self._ratio(follow, "target_height_ratio", 0.22)
    self.target_tolerance_ratio = self._ratio(follow, "target_tolerance_ratio", 0.07)
    self.too_close_height_ratio = self._ratio(follow, "too_close_height_ratio", 0.40)
    self.too_close_center_y_ratio = self._ratio(follow, "too_close_center_y_ratio", 0.72)
    self.min_distance_error = self._ratio(follow, "min_distance_error", 0.04)
    self.exit_velocity_threshold = max(
      0.0, as_float(follow, "exit_velocity_threshold", 0.05),
    )
    self.velocity_timeout_ms = max(100, as_int(follow, "velocity_timeout_ms", 1000))
    self.spin_gain = max(1.0, as_float(follow, "spin_gain", 14000.0))
    self.spin_damping = max(0.0, as_float(follow, "spin_damping", 2800.0))
    self.forward_gain = max(1.0, as_float(follow, "forward_gain", 30000.0))
    # Encoder closed-loop: allow small trim axes (Keyestudio needed high breakaway).
    self.max_spin_axis = max(1, min(AXIS_MAX, as_int(follow, "max_spin_axis", 9000)))
    self.min_spin_axis = max(1, min(self.max_spin_axis, as_int(follow, "min_spin_axis", 1200)))
    self.max_forward_axis = max(1, min(AXIS_MAX, as_int(follow, "max_forward_axis", 15000)))
    self.min_forward_axis = max(
      1, min(self.max_forward_axis, as_int(follow, "min_forward_axis", 1500)),
    )
    self.max_retreat_axis = max(
      1, min(self.max_forward_axis, as_int(follow, "max_retreat_axis", 4500)),
    )
    self.search_spin_axis = max(1, min(AXIS_MAX, as_int(follow, "search_spin_axis", 8000)))
    self.search_turn_ms = max(500, as_int(follow, "search_turn_ms", 2200))
    self.search_turn_deg = max(0.0, min(720.0, as_float(follow, "search_turn_deg", 360.0)))
    self.search_pause_ms = max(0, as_int(follow, "search_pause_ms", 800))
    self.search_retreat_ms = max(200, as_int(follow, "search_retreat_ms", 700))
    self.search_retreat_axis = max(
      1, min(self.max_retreat_axis, as_int(follow, "search_retreat_axis", 4500)),
    )
    self.compass_fix_spin_axis = max(
      1, min(AXIS_MAX, as_int(follow, "compass_fix_spin_axis", 5000)),
    )
    self.compass_fix_tolerance_deg = max(
      1.0, min(45.0, as_float(follow, "compass_fix_tolerance_deg", 8.0)),
    )
    self.compass_fix_timeout_ms = max(200, as_int(follow, "compass_fix_timeout_ms", 2500))
    self.horizontal_deadzone = self._ratio(follow, "horizontal_deadzone", 0.12)
    self.lost_search_ms = max(500, as_int(follow, "lost_search_ms", 2000))
    self.trajectory_max_points = max(4, min(64, as_int(follow, "trajectory_max_points", 24)))
    self.forward_axis_sign = self._axis_sign(follow, "forward_axis_sign", 1)
    self.spin_axis_sign = self._axis_sign(follow, "spin_axis_sign", 1)
    self.ball_diameter_cm = max(0.5, as_float(follow, "ball_diameter_cm", 3.5))
    self.depth_fusion_enabled = as_bool(follow, "depth_fusion_enabled", False)
    self.depth_model_path = as_str(
      follow, "depth_model_path", "/root/models/depth_anything_v2_vits.mud",
    )
    self.depth_interval_ms = max(0, as_int(follow, "depth_interval_ms", 200))
    self.depth_view = DepthViewMode.parse(as_str(follow, "depth_view", "blend"))
    self.depth_rgb_alpha = self._ratio(follow, "depth_rgb_alpha", 0.55)
    self.depth_show_contours = as_bool(follow, "depth_show_contours", False)
    self.depth_contour_low = max(1, as_int(follow, "depth_contour_low", 50))
    self.depth_contour_high = max(
      self.depth_contour_low + 1, as_int(follow, "depth_contour_high", 100),
    )
    self.depth_contour_alpha = self._ratio(follow, "depth_contour_alpha", 0.65)
    self.depth_contour_thickness = max(1, min(4, as_int(follow, "depth_contour_thickness", 2)))
    self.depth_ball_band_enabled = as_bool(follow, "depth_ball_band_enabled", True)
    self.depth_close_warmth = as_float(follow, "depth_close_warmth", 0.35)
    self.depth_far_warmth = as_float(follow, "depth_far_warmth", -0.10)
    self.depth_close_cm = max(1.0, as_float(follow, "depth_close_cm", 15.0))
    self.depth_far_cm = max(self.depth_close_cm + 1.0, as_float(follow, "depth_far_cm", 25.0))
    self.depth_near_ratio = self._ratio(follow, "depth_near_ratio", 0.35)
    self.depth_roi_top_ratio = self._ratio(follow, "depth_roi_top_ratio", 0.35)
    self.depth_roi_bottom_ratio = self._ratio(follow, "depth_roi_bottom_ratio", 0.85)
    self.depth_roi_left_ratio = self._ratio(follow, "depth_roi_left_ratio", 0.25)
    self.depth_roi_right_ratio = self._ratio(follow, "depth_roi_right_ratio", 0.75)

  def thresholds_for(self, color: str) -> list[list[int]]:
    """Return MaixPy LAB rows for one named color preset."""
    preset = self.color_presets.get(color) or self.color_presets[self.default_color]
    return preset.maix_thresholds()

  def next_color(self, color: str) -> str:
    """Return the next color name in the configured cycle."""
    return self.color_cycle.next_after(color)

  @staticmethod
  def _ratio(block: dict, key: str, default: float) -> float:
    """Read a normalized setting and keep it between zero and one."""
    return max(0.0, min(1.0, as_float(block, key, default)))

  @staticmethod
  def _axis_sign(block: dict, key: str, default: int) -> int:
    """Read an axis sign and normalize every non-negative value to one."""
    return -1 if as_int(block, key, default) < 0 else 1

  def _read_default_color(self, block: dict) -> str:
    """Read the startup color; must exist in ``colors``."""
    color = as_str(block, "color", "").strip().lower()
    if color in self.color_presets:
      return color
    return self.color_cycle.first()

  @staticmethod
  def _read_color_cycle(block: dict, presets: dict[str, BallColorPreset]) -> ColorNameCycle:
    """Ordered cycle for Menu/Start; defaults to sorted preset names."""
    ordered = as_str_list(block, "color_order")
    names = [name.strip().lower() for name in ordered if name.strip()]
    valid = [name for name in names if name in presets]
    if not valid:
      valid = sorted(presets.keys())
    return ColorNameCycle(valid)

  @staticmethod
  def _read_color_presets(block: dict) -> dict[str, BallColorPreset]:
    """Require ``ball_follow.colors`` from config (no hardcoded LAB)."""
    colors = block.get("colors")
    if not isinstance(colors, dict) or not colors:
      raise ValueError("config ball_follow.colors is required (LAB presets)")
    presets: dict[str, BallColorPreset] = {}
    for name, raw_rows in colors.items():
      key = str(name).strip().lower()
      rows = BallFollowSettings._parse_threshold_rows(raw_rows)
      if not rows:
        print(f"ball config: color {key!r} has no valid LAB rows — skipped")
        continue
      presets[key] = BallColorPreset(name=key, thresholds=LabThresholdSet(rows))
    if not presets:
      raise ValueError("config ball_follow.colors has no valid LAB presets")
    return presets

  @staticmethod
  def _parse_threshold_rows(value) -> list[LabThreshold]:
    """Parse a list of 6-int LAB rows into LabThreshold values."""
    if not isinstance(value, list) or not value:
      return []
    rows: list[LabThreshold] = []
    for candidate in value:
      if not isinstance(candidate, list) or len(candidate) != 6:
        continue
      try:
        nums = [int(round(float(item))) for item in candidate]
      except (TypeError, ValueError) as threshold_error:
        print(f"ball config: invalid LAB threshold ignored: {threshold_error}")
        continue
      rows.append(
        LabThreshold(
          l_min=nums[0], l_max=nums[1],
          a_min=nums[2], a_max=nums[3],
          b_min=nums[4], b_max=nums[5],
        )
      )
    return rows
