"""Fake depth plane with a warm left third for sampler tests."""

from __future__ import annotations


class FakeHotLeftDepth:
  """Turbo-like pixels: left third orange, elsewhere cool blue."""

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
    """Return warm RGB on the left third, cool elsewhere."""
    del y
    if x < self._width // 3:
      rgb = (220, 60, 10)
    else:
      rgb = (30, 80, 160)
    if rgbtuple:
      return rgb
    return [rgb[0] << 16 | rgb[1] << 8 | rgb[2]]
