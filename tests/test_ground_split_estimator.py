"""GroundSplitEstimator locks onto light-green turbo band."""

from __future__ import annotations

from lib.obstacle_nav.ground_split_estimator import GroundSplitEstimator


class _FakeDepth:
  """Orange floor below, light-green band at split_y, blue above."""

  def __init__(self, width: int, height: int, split_y: int) -> None:
    self._w = width
    self._h = height
    self._split = split_y

  def width(self) -> int:
    return self._w

  def height(self) -> int:
    return self._h

  def get_pixel(self, x: int, y: int, rgbtuple: bool = False):
    if y > self._split + 4:
      rgb = (220, 90, 20)  # orange floor
    elif abs(y - self._split) <= 4:
      rgb = (60, 200, 70)  # light green
    else:
      rgb = (30, 80, 180)  # blue far
    if rgbtuple:
      return rgb
    return [rgb[0] << 16 | rgb[1] << 8 | rgb[2]]


def test_propose_locks_on_green_not_orange() -> None:
  depth = _FakeDepth(100, 100, split_y=48)
  ratio = GroundSplitEstimator().propose(
    depth,
    frame_width=100,
    frame_height=100,
    floor_warmth=0.08,
    min_ratio=0.35,
    max_ratio=0.75,
  )
  assert ratio is not None
  assert 0.42 <= ratio <= 0.55
