"""Fake depth plane with a thin warm strip on the far-left edge."""

from __future__ import annotations


class FakeEdgeHotSpotDepth:
  """Only columns x < 4 are warm — peak must catch what mean would dilute."""

  def __init__(self, width: int, height: int) -> None:
    """Remember plane size."""
    self._width = width
    self._height = height

  def width(self) -> int:
    """Return plane width."""
    return self._width

  def height(self) -> int:
    """Return plane height."""
    return self._height

  def get_pixel(self, x: int, y: int, rgbtuple: bool = False):
    """Return warm RGB on a thin left edge, cool elsewhere."""
    del y
    if x < 4:
      rgb = (230, 40, 10)
    else:
      rgb = (40, 90, 150)
    if rgbtuple:
      return rgb
    return [rgb[0] << 16 | rgb[1] << 8 | rgb[2]]
