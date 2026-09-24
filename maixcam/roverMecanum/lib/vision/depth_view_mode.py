"""How depth fusion paints the HUD (NN always runs when fusion is on)."""

from __future__ import annotations

from enum import Enum


class DepthViewMode(Enum):
  """Display mode for depth fusion; inference still runs in every mode."""

  BLEND = "blend"  # RGB + depth alpha blend (costly)
  DEPTH = "depth"  # replace frame with upscaled turbo depth
  RGB = "rgb"  # keep camera RGB; depth used only for ball band / near

  @classmethod
  def parse(cls, raw: str, default: DepthViewMode | None = None) -> DepthViewMode:
    """Map a config string to a mode; unknown values fall back to default."""
    fallback = default if default is not None else cls.BLEND
    key = str(raw or "").strip().lower()
    for mode in cls:
      if mode.value == key:
        return mode
    return fallback
