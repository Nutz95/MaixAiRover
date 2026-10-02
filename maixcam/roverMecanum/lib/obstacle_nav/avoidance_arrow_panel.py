"""Big HUD arrow / vector for avoidance hint in manual / follow."""

from __future__ import annotations

from lib.obstacle_nav.avoidance_hint import AvoidanceHint
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading

try:
  from maix import image as maix_image
except Exception as maix_import_error:
  print(f"avoidance arrow: maix unavailable: {maix_import_error}")
  maix_image = None


class AvoidanceArrowPanel:
  """Draw a coarse dodge vector near the bottom of the frame."""

  def draw(self, img, hint: AvoidanceHint) -> None:
    """Paint a thick arrow from a discrete hint; no-op when NONE."""
    if maix_image is None or hint is AvoidanceHint.NONE:
      return
    w = img.width()
    h = img.height()
    cx = w // 2
    cy = int(h * 0.78)
    color = maix_image.Color.from_rgb(255, 200, 40)
    if hint is AvoidanceHint.STRAFE_LEFT:
      self._arrow(img, cx + 40, cy, cx - 50, cy, color)
    elif hint is AvoidanceHint.STRAFE_RIGHT:
      self._arrow(img, cx - 40, cy, cx + 50, cy, color)
    elif hint is AvoidanceHint.REVERSE:
      self._arrow(img, cx, cy - 30, cx, cy + 50, color)
    elif hint is AvoidanceHint.STOP_FORWARD:
      img.draw_line(cx - 40, cy, cx + 40, cy, color, thickness=6)

  def draw_vector(self, img, reading: ObstacleBandReading) -> None:
    """Paint a continuous dodge vector from left/right/center excess warmth."""
    if maix_image is None or reading.column_count() < 1:
      return
    # Right hotter → push left (negative screen x); center hot → reverse (down).
    dx = (reading.left_mean() - reading.right_mean()) * 180.0
    dy = max(0.0, reading.center_warmth()) * 160.0
    if abs(dx) < 12 and dy < 12:
      return
    cx = img.width() // 2
    cy = int(img.height() * 0.78)
    x1 = int(cx + max(-70, min(70, dx)))
    y1 = int(cy + max(0, min(60, dy)))
    color = maix_image.Color.from_rgb(255, 220, 60)
    self._arrow(img, cx, cy, x1, y1, color)

  @staticmethod
  def _arrow(img, x0: int, y0: int, x1: int, y1: int, color) -> None:
    img.draw_line(x0, y0, x1, y1, color, thickness=8)
    dx = x1 - x0
    dy = y1 - y0
    if abs(dx) >= abs(dy):
      sign = 1 if dx >= 0 else -1
      img.draw_line(x1, y1, x1 - sign * 22, y1 - 16, color, thickness=6)
      img.draw_line(x1, y1, x1 - sign * 22, y1 + 16, color, thickness=6)
    else:
      sign = 1 if dy >= 0 else -1
      img.draw_line(x1, y1, x1 - 16, y1 - sign * 22, color, thickness=6)
      img.draw_line(x1, y1, x1 + 16, y1 - sign * 22, color, thickness=6)
