"""Full-screen opaque peripheral checklist with OK dismiss."""

from maix import image

from lib.ui.ui_rect import UiRect


class ChecklistPanel:
  """Opaque post-connect health screen (green/red dots + OK button)."""

  def __init__(self, width: int, height: int) -> None:
    self.width = width
    self.height = height
    # Sit above the HUD DISC/DBG row so a stuck finger cannot visually align.
    btn_h = 72
    gap = 24
    self._ok_rect = UiRect(gap, height - btn_h - 110, width - gap * 2, btn_h)

  def ok_rect(self) -> UiRect:
    """Return the OK button hit rectangle."""
    return self._ok_rect

  def draw(self, img, checklist) -> None:
    """Paint an opaque checklist screen; checklist may be None while probing."""
    img.draw_rect(0, 0, self.width, self.height, image.Color.from_rgb(12, 14, 20), thickness=-1)
    img.draw_rect(8, 8, 44, 44, image.Color.from_rgb(30, 30, 35), thickness=-1)
    img.draw_string(18, 16, "<", image.COLOR_WHITE, scale=1.4)
    title = "Peripherals"
    title_scale = 1.6
    size = image.string_size(title, scale=title_scale, thickness=2)
    img.draw_string(
      (self.width - size.width()) // 2,
      28,
      title,
      image.COLOR_WHITE,
      scale=title_scale,
    )

    y = 90
    if checklist is None:
      img.draw_string(32, y, "Checking devices…", image.Color.from_rgb(180, 180, 180), scale=1.3)
      self._draw_ok_button(img, enabled=False)
      return

    for item in checklist.checks:
      self._draw_row(img, 28, y, item.ok, item.name, item.detail)
      y += 70
      if y > self._ok_rect.y - 24:
        break

    self._draw_ok_button(img, enabled=True)

  def _draw_row(self, img, x: int, y: int, ok: bool, name: str, detail: str) -> None:
    color = image.Color.from_rgb(40, 200, 90) if ok else image.Color.from_rgb(220, 60, 60)
    img.draw_circle(x + 16, y + 18, 14, color, thickness=-1)
    img.draw_circle(x + 16, y + 18, 14, image.COLOR_WHITE, thickness=2)
    img.draw_string(x + 44, y + 4, name, image.COLOR_WHITE, scale=1.35)
    text = detail if len(detail) <= 36 else detail[:35] + "…"
    img.draw_string(x + 44, y + 34, text, image.Color.from_rgb(160, 165, 175), scale=1.0)

  def _draw_ok_button(self, img, enabled: bool) -> None:
    rect = self._ok_rect
    color = (
      image.Color.from_rgb(40, 140, 70) if enabled else image.Color.from_rgb(50, 50, 55)
    )
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, color, thickness=-1)
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, image.COLOR_WHITE, thickness=2)
    label = "OK" if enabled else "…"
    size = image.string_size(label, scale=1.5, thickness=1)
    img.draw_string(
      rect.x + (rect.width - size.width()) // 2,
      rect.y + (rect.height - size.height()) // 2,
      label,
      image.COLOR_WHITE,
      scale=1.5,
    )
