"""depth_pixel unpacks Maix get_pixel(rgbtuple=True) and packed forms."""

from __future__ import annotations

from lib.vision.depth_pixel import pixel_rgb, pixel_warmth


class _Fake:
  def __init__(self) -> None:
    self._w = 4
    self._h = 4

  def width(self) -> int:
    return self._w

  def height(self) -> int:
    return self._h

  def get_pixel(self, x, y, rgbtuple=False):
    if rgbtuple:
      return (200, 40, 20)
    return [200 << 16 | 40 << 8 | 20]


def test_rgbtuple_path() -> None:
  img = _Fake()
  assert pixel_rgb(img, 1, 1) == (200, 40, 20)
  assert abs(pixel_warmth(img, 1, 1) - (200 - 20) / 255.0) < 0.01
