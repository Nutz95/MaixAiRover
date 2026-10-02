"""HUD ground split line only (no blue obstacle wash)."""

from __future__ import annotations

from maix import image

from lib.obstacle_nav.nav_roi_layout import NavRoiLayout


class NavRoiGuidePanel:
  """Paint the calibrated ground horizon — tilt / floor cue only."""

  def draw(self, img, layout: NavRoiLayout) -> None:
    """Draw the green ground_top line (obstacle boxes are painted separately)."""
    width = img.width()
    height = img.height()
    ground_y = layout.ground_top_y(height)
    ground_color = image.Color.from_rgb(80, 220, 120)
    img.draw_line(0, ground_y, width - 1, ground_y, ground_color, thickness=2)
