"""Tilted-camera ROI layout: ground strip vs obstacle band (ratios → pixels)."""

from __future__ import annotations

from lib.obstacle_nav.nav_roi_pixel_box import NavRoiPixelBox
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


class NavRoiLayout:
  """Map ``obstacle_nav`` ROI ratios to pixel boxes for HUD and algo crops."""

  def __init__(self, settings: ObstacleNavSettings) -> None:
    """Bind to current obstacle_nav settings."""
    self._settings = settings

  def ground_box(self, width: int, height: int) -> NavRoiPixelBox:
    """Lower image band treated as ground (ball / OF ground)."""
    top = self._clamp_y(self._settings.ground_top_ratio, height)
    return NavRoiPixelBox(left=0, top=top, right=max(1, width), bottom=max(1, height))

  def obstacle_box(self, width: int, height: int) -> NavRoiPixelBox:
    """Band above the ground line used for near-field obstacle depth/OF."""
    top = self._clamp_y(self._settings.obstacle_top_ratio, height)
    bottom = self._clamp_y(self._settings.ground_top_ratio, height)
    left = self._clamp_x(self._settings.obstacle_left_ratio, width)
    right = self._clamp_x(self._settings.obstacle_right_ratio, width)
    if bottom < top:
      top, bottom = bottom, top
    if right < left:
      left, right = right, left
    return NavRoiPixelBox(left=left, top=top, right=right, bottom=bottom)

  def ground_top_y(self, height: int) -> int:
    """Pixel Y of the ground / rest split line."""
    return self._clamp_y(self._settings.ground_top_ratio, height)

  def obstacle_top_y(self, height: int) -> int:
    """Pixel Y of the upper obstacle-band line."""
    return self._clamp_y(self._settings.obstacle_top_ratio, height)

  @staticmethod
  def _clamp_y(ratio: float, height: int) -> int:
    return max(0, min(height, int(round(ratio * height))))

  @staticmethod
  def _clamp_x(ratio: float, width: int) -> int:
    return max(0, min(width, int(round(ratio * width))))
