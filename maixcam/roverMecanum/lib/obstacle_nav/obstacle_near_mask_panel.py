"""Paint clear L/C/R obstacle zones above the ground line."""

from __future__ import annotations

from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.nav_roi_pixel_box import NavRoiPixelBox
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading

try:
  from maix import image as maix_image
except Exception as maix_import_error:
  print(f"obstacle near mask: maix unavailable: {maix_import_error}")
  maix_image = None


class ObstacleNearMaskPanel:
  """Draw big red/orange blocks for left / center / right near obstacles."""

  def draw_from_reading(
    self,
    img,
    layout: NavRoiLayout,
    reading: ObstacleBandReading,
    *,
    close_warmth: float,
    caution_warmth: float,
  ) -> None:
    """Paint last L/C/R hits on the live RGB frame (persists between depth ticks)."""
    if maix_image is None:
      return
    box = layout.obstacle_box(img.width(), img.height())
    if box.is_empty():
      return
    third = max(1, box.width // 3)
    zones = (
      (0, third, "L", reading.left),
      (third, 2 * third, "C", reading.center),
      (2 * third, box.width, "R", reading.right),
    )
    warn = maix_image.Color.from_rgb(255, 140, 30)
    danger = maix_image.Color.from_rgb(255, 40, 40)
    for x0_off, x1_off, label, warmth in zones:
      if warmth < caution_warmth:
        continue
      color = danger if warmth >= close_warmth else warn
      zone = NavRoiPixelBox(
        left=box.left + x0_off,
        top=box.top,
        right=box.left + x1_off,
        bottom=box.bottom,
      )
      self._paint_zone(img, zone, color, label)

  @staticmethod
  def _paint_zone(img, box: NavRoiPixelBox, color, label: str) -> None:
    w = box.width
    h = box.height
    if w <= 0 or h <= 0:
      return
    img.draw_rect(box.left, box.top, w, h, color, thickness=-1)
    img.draw_rect(box.left, box.top, w, h, maix_image.COLOR_WHITE, thickness=3)
    img.draw_string(
      box.left + 6, box.top + 6, label, maix_image.COLOR_WHITE, scale=2.0,
    )
