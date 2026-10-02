"""Paint clear obstacle column zones above the ground line."""

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
  """Draw red/orange blocks for each near obstacle column."""

  def draw_from_reading(
    self,
    img,
    layout: NavRoiLayout,
    reading: ObstacleBandReading,
    *,
    close_warmth: float,
    caution_warmth: float,
  ) -> None:
    """Paint last column hits on the live RGB frame (persists between depth ticks)."""
    if maix_image is None:
      return
    box = layout.obstacle_box(img.width(), img.height())
    if box.is_empty() or reading.column_count() < 1:
      return
    count = reading.column_count()
    warn = maix_image.Color.from_rgb(255, 140, 30)
    danger = maix_image.Color.from_rgb(255, 40, 40)
    for index in range(count):
      warmth = reading.warmth_at(index)
      if warmth < caution_warmth:
        continue
      color = danger if warmth >= close_warmth else warn
      x0 = (box.width * index) // count
      x1 = (box.width * (index + 1)) // count
      zone = NavRoiPixelBox(
        left=box.left + x0,
        top=box.top,
        right=box.left + x1,
        bottom=box.bottom,
      )
      self._paint_zone(img, zone, color, str(index))

  @staticmethod
  def _paint_zone(img, box: NavRoiPixelBox, color, label: str) -> None:
    width = box.width
    height = box.height
    if width <= 0 or height <= 0:
      return
    img.draw_rect(box.left, box.top, width, height, color, thickness=-1)
    img.draw_rect(box.left, box.top, width, height, maix_image.COLOR_WHITE, thickness=2)
    img.draw_string(
      box.left + 4, box.top + 4, label, maix_image.COLOR_WHITE, scale=1.2,
    )
