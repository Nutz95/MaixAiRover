"""Axis-aligned pixel crop box for nav ROI bands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavRoiPixelBox:
  """Inclusive-exclusive pixel rectangle ``[left, right) × [top, bottom)``."""

  left: int
  top: int
  right: int
  bottom: int

  @property
  def width(self) -> int:
    """Return box width in pixels."""
    return max(0, self.right - self.left)

  @property
  def height(self) -> int:
    """Return box height in pixels."""
    return max(0, self.bottom - self.top)

  def is_empty(self) -> bool:
    """True when the box has no area."""
    return self.width <= 0 or self.height <= 0
