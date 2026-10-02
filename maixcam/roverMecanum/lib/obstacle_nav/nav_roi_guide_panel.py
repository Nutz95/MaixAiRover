"""Thin HUD guides for ground vs obstacle ROI (camera tilt alignment)."""

from __future__ import annotations

from maix import image

from lib.obstacle_nav.nav_roi_layout import NavRoiLayout


class NavRoiGuidePanel:
  """Paint fine split lines + obstacle-band fill on the teleop HUD."""

  def draw(self, img, layout: NavRoiLayout) -> None:
    """Draw ground horizon + filled obstacle corridor on ``img``."""
    width = img.width()
    height = img.height()
    ground_y = layout.ground_top_y(height)
    obstacle_y = layout.obstacle_top_y(height)
    box = layout.obstacle_box(width, height)
    obstacle_color = image.Color.from_rgb(80, 160, 255)
    ground_color = image.Color.from_rgb(80, 220, 120)
    self._fill_obstacle_band(img, box, obstacle_color)
    # Ground split (full width) — primary tilt cue.
    img.draw_line(0, ground_y, width - 1, ground_y, ground_color, thickness=1)
    # Obstacle band upper edge + side rails (crop guide for depth/OF).
    img.draw_line(0, obstacle_y, width - 1, obstacle_y, obstacle_color, thickness=1)
    if not box.is_empty():
      img.draw_line(box.left, box.top, box.left, box.bottom - 1, obstacle_color, thickness=1)
      img.draw_line(box.right - 1, box.top, box.right - 1, box.bottom - 1, obstacle_color, thickness=1)
      # Mid vertical = corridor center (left vs right obstacle half).
      mid_x = (box.left + box.right) // 2
      img.draw_line(mid_x, box.top, mid_x, box.bottom - 1, obstacle_color, thickness=1)

  @staticmethod
  def _fill_obstacle_band(img, box, color) -> None:
    """Semi-transparent fill so the obstacle ROI is obvious while tilting."""
    if box.is_empty():
      return
    try:
      plane = image.Image(box.width, box.height, bg=color)
    except Exception as plane_error:
      print(f"nav roi: fill plane: {plane_error}")
      return
    # ~25% opacity — enough to see the band without hiding the scene.
    alpha = 64
    try:
      if hasattr(img, "draw_image"):
        img.draw_image(box.left, box.top, plane, alpha=alpha)
        return
    except Exception as draw_error:
      print(f"nav roi: draw_image alpha: {draw_error}")
    try:
      if hasattr(img, "blend"):
        # blend expects full-frame; fall back to hatch.
        pass
    except Exception as blend_error:
      print(f"nav roi: blend: {blend_error}")
    # Hatch fallback (no alpha API).
    step = 8
    for y in range(box.top, box.bottom, step):
      img.draw_line(box.left, y, box.right - 1, y, color, thickness=1)
