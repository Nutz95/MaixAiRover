"""Typed camera preview settings from config.json ``camera`` block."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraConfig:
  """Camera enable flag and HUD display rate."""

  enabled: bool = False
  width: int = 640
  height: int = 480
  fps: int = 30
  format: str = "rgb888"
  display_fps: int = 30

  @classmethod
  def from_mapping(cls, raw: dict) -> "CameraConfig":
    """Build from the ``camera`` object in config.json."""
    if not isinstance(raw, dict):
      raw = {}
    return cls(
      enabled=bool(raw.get("enabled", False)),
      width=int(raw.get("width", 640)),
      height=int(raw.get("height", 480)),
      fps=int(raw.get("fps", 30)),
      format=str(raw.get("format", "rgb888")),
      display_fps=max(5, min(30, int(raw.get("display_fps", 20)))),
    )
