"""Typed obstacle / IMU calib settings from config.json."""

from __future__ import annotations

from lib.config.config_parse_helpers import as_bool, as_float, as_int, section


class ObstacleNavSettings:
  """Feature flags and thresholds for IMU calib and stuck detection."""

  def __init__(self, raw: dict) -> None:
    """Load the ``obstacle_nav`` section."""
    block = section(raw, "obstacle_nav")
    self.enabled = as_bool(block, "enabled", True)
    self.calib_after_connect = as_bool(block, "calib_after_connect", True)
    self.calib_skippable = as_bool(block, "calib_skippable", True)
    self.stuck_window_ms = max(50, as_int(block, "stuck_window_ms", 300))
    self.yaw_error_deg = max(1.0, as_float(block, "yaw_error_deg", 25.0))
    self.pitch_lift_deg = max(1.0, as_float(block, "pitch_lift_deg", 8.0))
    self.roll_bump_deg = max(1.0, as_float(block, "roll_bump_deg", 6.0))
    self.cmd_axis_threshold = max(100, as_int(block, "cmd_axis_threshold", 800))
    self.encoder_tick_threshold = max(1, as_int(block, "encoder_tick_threshold", 3))
    self.overlay_clear_ms = max(100, as_int(block, "overlay_clear_ms", 500))
    self.accel_impact_mps2 = max(0.2, as_float(block, "accel_impact_mps2", 3.0))
    self.accel_crash_mps2 = max(1.0, as_float(block, "accel_crash_mps2", 5.0))
    self.impact_hold_ms = max(40, as_int(block, "impact_hold_ms", 150))
    self.soft_impact_enabled = as_bool(block, "soft_impact_enabled", False)
    self.accel_launch_mps2 = max(0.05, as_float(block, "accel_launch_mps2", 0.50))
    self.slip_delta_v_mps = max(0.02, as_float(block, "slip_delta_v_mps", 0.12))
    # Off by default: mecanum vibration + cruise a≈0 false-triggers slip.
    self.slip_enabled = as_bool(block, "slip_enabled", False)
    self.probe_log_ms = max(200, as_int(block, "probe_log_ms", 500))
    self.probe_tcp_port = max(0, as_int(block, "probe_tcp_port", 9400))
    # Collision HUD / detector (false positives — park while building vision).
    self.stuck_detection_enabled = as_bool(block, "stuck_detection_enabled", True)
    self.calib_creep_axis = max(500, as_int(block, "calib_creep_axis", 7000))
    self.calib_spin_axis = max(500, as_int(block, "calib_spin_axis", 9000))
    self.calib_motion_ms = max(50, as_int(block, "calib_motion_ms", 600))
    self.calib_rest_ms = max(50, as_int(block, "calib_rest_ms", 800))
    # Tilted-cam ROI: below ground_top = ground; obstacle band above it.
    self.show_roi_guides = as_bool(block, "show_roi_guides", True)
    self.ground_top_ratio = self._ratio(block, "ground_top_ratio", 0.50)
    self.obstacle_top_ratio = self._ratio(block, "obstacle_top_ratio", 0.18)
    self.obstacle_left_ratio = self._ratio(block, "obstacle_left_ratio", 0.08)
    self.obstacle_right_ratio = self._ratio(block, "obstacle_right_ratio", 0.92)
    self.obstacle_band_count = max(3, min(9, as_int(block, "obstacle_band_count", 5)))
    # Depth ground-split after IMU (Xbox A confirm). Runtime-only until reboot.
    self.depth_ground_calib = as_bool(block, "depth_ground_calib", True)
    self.ground_floor_warmth = as_float(block, "ground_floor_warmth", 0.08)
    # Soft avoidance from L/C/R warmth in the obstacle band.
    self.avoidance_enabled = as_bool(block, "avoidance_enabled", True)
    self.avoidance_close_warmth = as_float(block, "avoidance_close_warmth", 0.22)
    self.avoidance_caution_warmth = as_float(block, "avoidance_caution_warmth", 0.10)
    self.avoidance_strafe_axis = max(500, as_int(block, "avoidance_strafe_axis", 12000))
    self.avoidance_reverse_axis = max(500, as_int(block, "avoidance_reverse_axis", 8000))

  def set_ground_top_ratio(self, ratio: float) -> None:
    """Apply a confirmed ground split (session only — not written to disk)."""
    self.ground_top_ratio = max(0.0, min(1.0, float(ratio)))

  @staticmethod
  def _ratio(block: dict, key: str, default: float) -> float:
    return max(0.0, min(1.0, as_float(block, key, default)))
