"""Full-screen Yahboom USB link gate with manual retry."""

from maix import image

from lib.ui.ui_rect import UiRect


class DriveLinkPanel:
  """Opaque startup screen when the Yahboom CH340/USB host is missing."""

  def __init__(self, width: int, height: int) -> None:
    """Layout title, detail, and a RETRY button above the HUD chrome."""
    self.width = width
    self.height = height
    btn_h = 72
    gap = 24
    self._retry_rect = UiRect(gap, height - btn_h - 110, width - gap * 2, btn_h)

  def retry_rect(self) -> UiRect:
    """Return the RETRY button hit rectangle."""
    return self._retry_rect

  def draw(self, img, detail: str, *, busy: bool = False) -> None:
    """Paint link-missing UI; ``busy`` greys out RETRY while reconnecting."""
    img.draw_rect(0, 0, self.width, self.height, image.Color.from_rgb(12, 14, 20), thickness=-1)
    img.draw_rect(8, 8, 44, 44, image.Color.from_rgb(30, 30, 35), thickness=-1)
    img.draw_string(18, 16, "<", image.COLOR_WHITE, scale=1.4)

    title = "Yahboom USB"
    title_scale = 1.6
    size = image.string_size(title, scale=title_scale, thickness=2)
    img.draw_string(
      (self.width - size.width()) // 2,
      28,
      title,
      image.COLOR_WHITE,
      scale=title_scale,
    )

    muted = image.Color.from_rgb(180, 180, 180)
    warn = image.Color.from_rgb(230, 160, 60)
    y = 110
    img.draw_string(32, y, "USB link missing / lost", warn, scale=1.35)
    y += 48
    img.draw_string(32, y, "Check Micro-USB data cable", muted, scale=1.15)
    y += 36
    img.draw_string(32, y, "and Yahboom board power,", muted, scale=1.15)
    y += 36
    img.draw_string(32, y, "then tap RETRY.", muted, scale=1.15)
    y += 56
    text = (detail or "waiting…").strip()
    if len(text) > 48:
      text = text[:47] + "…"
    img.draw_string(32, y, text, image.COLOR_WHITE, scale=1.05)
    self._draw_retry(img, enabled=not busy)

  def _draw_retry(self, img, *, enabled: bool) -> None:
    rect = self._retry_rect
    color = (
      image.Color.from_rgb(40, 120, 180) if enabled else image.Color.from_rgb(50, 50, 55)
    )
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, color, thickness=-1)
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, image.COLOR_WHITE, thickness=2)
    label = "RETRY" if enabled else "…"
    size = image.string_size(label, scale=1.5, thickness=1)
    img.draw_string(
      rect.x + (rect.width - size.width()) // 2,
      rect.y + (rect.height - size.height()) // 2,
      label,
      image.COLOR_WHITE,
      scale=1.5,
    )
