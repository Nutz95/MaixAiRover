"""ObstacleBandSampler L/C/R means + ball mask."""

from __future__ import annotations

from lib.ball_follow.ball_observation import BallObservation
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.obstacle_band_sampler import ObstacleBandSampler
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


class _HotLeftDepth:
  def __init__(self, width: int, height: int) -> None:
    self._w = width
    self._h = height

  def width(self) -> int:
    return self._w

  def height(self) -> int:
    return self._h

  def get_pixel(self, x: int, y: int, rgbtuple: bool = False):
    # Left third warm.
    if x < self._w // 3:
      rgb = (220, 60, 10)
    else:
      rgb = (30, 80, 160)
    if rgbtuple:
      return rgb
    return [rgb[0] << 16 | rgb[1] << 8 | rgb[2]]


def test_left_third_warmer() -> None:
  settings = ObstacleNavSettings({
    "obstacle_nav": {
      "ground_top_ratio": 0.70,
      "obstacle_top_ratio": 0.20,
      "obstacle_left_ratio": 0.0,
      "obstacle_right_ratio": 1.0,
    },
  })
  layout = NavRoiLayout(settings)
  depth = _HotLeftDepth(60, 60)
  reading = ObstacleBandSampler().sample(
    depth, layout, frame_width=60, frame_height=60,
  )
  assert reading.left > reading.right
  assert reading.left > 0.3


def test_ball_mask_skips_hot_cell() -> None:
  settings = ObstacleNavSettings({
    "obstacle_nav": {
      "ground_top_ratio": 0.80,
      "obstacle_top_ratio": 0.10,
      "obstacle_left_ratio": 0.0,
      "obstacle_right_ratio": 1.0,
    },
  })
  layout = NavRoiLayout(settings)
  depth = _HotLeftDepth(60, 60)
  ball = BallObservation(
    center_x=10,
    center_y=30,
    width=40,
    height=40,
    area=100,
    score=1.0,
    timestamp_ms=0,
    image_width=60,
    image_height=60,
  )
  reading = ObstacleBandSampler().sample(
    depth, layout, frame_width=60, frame_height=60, ball=ball,
  )
  # Mask covers most of the left hot zone → left mean drops.
  assert reading.left < 0.5
