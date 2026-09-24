"""UI hit-test rectangle."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UiRect:
  """Axis-aligned rectangle in display coordinates."""

  x: int
  y: int
  width: int
  height: int

  def contains(self, px: int, py: int) -> bool:
    """Return True if the point lies inside this rectangle."""
    return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height
