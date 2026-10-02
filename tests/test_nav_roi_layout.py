"""NavRoiLayout pixel boxes from obstacle_nav ratios."""

from __future__ import annotations

from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


def _layout(**overrides) -> NavRoiLayout:
  block = {
    "ground_top_ratio": 0.50,
    "obstacle_top_ratio": 0.18,
    "obstacle_left_ratio": 0.15,
    "obstacle_right_ratio": 0.85,
    **overrides,
  }
  return NavRoiLayout(ObstacleNavSettings({"obstacle_nav": block}))


def test_ground_box_is_lower_band() -> None:
  layout = _layout()
  box = layout.ground_box(200, 100)
  assert box.left == 0
  assert box.right == 200
  assert box.top == 50
  assert box.bottom == 100


def test_obstacle_box_sits_above_ground() -> None:
  layout = _layout()
  box = layout.obstacle_box(200, 100)
  assert box.top == 18
  assert box.bottom == 50
  assert box.left == 30
  assert box.right == 170
  assert not box.is_empty()
