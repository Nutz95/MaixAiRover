"""Top-down rover collision highlight overlay."""

from maix import image

from lib.obstacle_nav.collision_side import CollisionSide
from lib.obstacle_nav.stuck_level import StuckLevel
from lib.obstacle_nav.stuck_report import StuckReport


class StuckOverlayPanel:
  """Semi-opaque card with a top-down chassis and lit contact edge."""

  def __init__(self, width: int, height: int) -> None:
    """Anchor the card in the upper-right of the HUD."""
    self.width = width
    self.height = height
    self._card_w = 260
    self._card_h = 240
    self._card_x = max(8, width - self._card_w - 8)
    self._card_y = 48

  def draw(self, img, report: StuckReport) -> None:
    """Paint the stuck card when level is warn or stuck."""
    if report.level == StuckLevel.OK:
      return
    x = self._card_x
    y = self._card_y
    img.draw_rect(
      x, y, self._card_w, self._card_h,
      image.Color.from_rgb(18, 20, 28),
      thickness=-1,
    )
    img.draw_rect(
      x, y, self._card_w, self._card_h,
      image.Color.from_rgb(240, 150, 60),
      thickness=3,
    )
    title = "STUCK" if report.level == StuckLevel.STUCK else "WARN"
    img.draw_string(x + 14, y + 12, title, image.Color.from_rgb(255, 180, 80), scale=2.2)
    img.draw_string(
      x + 14, y + 52,
      f"SIDE {report.side.value.upper()}",
      image.COLOR_WHITE,
      scale=1.7,
    )
    detail = report.detail if len(report.detail) <= 26 else report.detail[:25] + "..."
    if detail:
      img.draw_string(
        x + 14, y + 88,
        detail,
        image.Color.from_rgb(180, 185, 195),
        scale=1.2,
      )
    self._draw_rover(img, x + 55, y + 120, report.side)

  def _draw_rover(self, img, ox: int, oy: int, side: CollisionSide) -> None:
    body_w, body_h = 150, 95
    body = image.Color.from_rgb(55, 60, 70)
    hot = image.Color.from_rgb(230, 70, 60)
    img.draw_rect(ox, oy, body_w, body_h, body, thickness=-1)
    img.draw_rect(ox, oy, body_w, body_h, image.COLOR_WHITE, thickness=2)
    img.draw_rect(ox + body_w // 2 - 14, oy - 8, 28, 8, image.COLOR_WHITE, thickness=-1)
    edges = {
      CollisionSide.FRONT: (ox, oy, body_w, 12),
      CollisionSide.REAR: (ox, oy + body_h - 12, body_w, 12),
      CollisionSide.LEFT: (ox, oy, 12, body_h),
      CollisionSide.RIGHT: (ox + body_w - 12, oy, 12, body_h),
    }
    if side in edges:
      ex, ey, ew, eh = edges[side]
      img.draw_rect(ex, ey, ew, eh, hot, thickness=-1)
    elif side == CollisionSide.UNKNOWN:
      img.draw_rect(ox + 6, oy + 6, body_w - 12, body_h - 12, hot, thickness=3)
