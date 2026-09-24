"""Typed teleop feel settings from config.json ``rover`` block."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoverConfig:
  """Stick shaping, send rate, and session speed limits."""

  max_speed: int = 255
  send_interval_ms: int = 15
  deadzone_percent: int = 0
  axis_sensitivity_percent: int = 100
  axis_expo: float = 1.6
  axis_curve: str = "expo"
  speed_step: int = 5

  @classmethod
  def from_mapping(cls, raw: dict) -> "RoverConfig":
    """Build from the ``rover`` object in config.json."""
    if not isinstance(raw, dict):
      raw = {}
    curve = str(raw.get("axis_curve", "expo")).strip().lower()
    if curve not in ("expo", "log", "linear"):
      curve = "expo"
    return cls(
      max_speed=max(0, min(255, int(raw.get("max_speed", 255)))),
      send_interval_ms=max(1, int(raw.get("send_interval_ms", 15))),
      deadzone_percent=max(0, min(100, int(raw.get("deadzone_percent", 0)))),
      axis_sensitivity_percent=max(
        1, min(100, int(raw.get("axis_sensitivity_percent", 100))),
      ),
      axis_expo=max(0.3, min(3.0, float(raw.get("axis_expo", 1.6)))),
      axis_curve=curve,
      speed_step=max(1, int(raw.get("speed_step", 5))),
    )
