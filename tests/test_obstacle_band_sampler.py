"""ObstacleBandSampler multi-column peaks + ball mask."""

from __future__ import annotations

from fake_edge_hot_spot_depth import FakeEdgeHotSpotDepth
from fake_hot_left_depth import FakeHotLeftDepth
from lib.ball_follow.ball_observation import BallObservation
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.obstacle_band_sampler import ObstacleBandSampler
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


def test_left_third_warmer() -> None:
  settings = ObstacleNavSettings({
    "obstacle_nav": {
      "ground_top_ratio": 0.70,
      "obstacle_top_ratio": 0.20,
      "obstacle_left_ratio": 0.0,
      "obstacle_right_ratio": 1.0,
      "obstacle_band_count": 5,
    },
  })
  layout = NavRoiLayout(settings)
  depth = FakeHotLeftDepth(60, 60)
  reading = ObstacleBandSampler().sample(
    depth, layout, frame_width=60, frame_height=60, column_count=5,
  )
  assert reading.warmth_at(0) > reading.warmth_at(4)
  assert reading.warmth_at(0) > 0.3


def test_edge_hotspot_triggers_peak() -> None:
  settings = ObstacleNavSettings({
    "obstacle_nav": {
      "ground_top_ratio": 0.80,
      "obstacle_top_ratio": 0.10,
      "obstacle_left_ratio": 0.0,
      "obstacle_right_ratio": 1.0,
      "obstacle_band_count": 5,
    },
  })
  layout = NavRoiLayout(settings)
  depth = FakeEdgeHotSpotDepth(60, 60)
  reading = ObstacleBandSampler().sample(
    depth, layout, frame_width=60, frame_height=60, column_count=5,
  )
  # Top-k mean must still catch a narrow edge obstacle.
  assert reading.warmth_at(0) > 0.5
  assert reading.warmth_at(0) > reading.warmth_at(2)


def test_ball_mask_skips_hot_cell() -> None:
  settings = ObstacleNavSettings({
    "obstacle_nav": {
      "ground_top_ratio": 0.80,
      "obstacle_top_ratio": 0.10,
      "obstacle_left_ratio": 0.0,
      "obstacle_right_ratio": 1.0,
      "obstacle_band_count": 5,
    },
  })
  layout = NavRoiLayout(settings)
  depth = FakeHotLeftDepth(60, 60)
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
    depth, layout, frame_width=60, frame_height=60, column_count=5, ball=ball,
  )
  assert reading.warmth_at(0) < 0.5
