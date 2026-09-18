"""Full-screen HUD overlay for camera + controller state."""

from maix import image

from lib.controller_button import ControllerButton
from lib.ui_rect import UiRect


class UiDrawer:
  """Full-screen HUD overlay (portrait) for camera + controller state."""

  SPEED_BAR_H = 22

  def __init__(self, width: int, height: int) -> None:
    self.width = width
    self.height = height
    self._img_back = self._load_back_btn(width)
    self._layout_buttons()

  def _layout_buttons(self) -> None:
    pad = 8
    back_size = 44
    self._back_pad = UiRect(pad, pad, back_size, back_size)
    disc_w, disc_h = 64, 40
    self._disconnect_rect = UiRect(self.width - disc_w - pad, pad, disc_w, disc_h)
    # Finger-friendly PAIR / CONNECT (bottom bar).
    btn_h = 72
    gap = 12
    y = self.height - btn_h - 10
    half_w = (self.width - gap * 3) // 2
    self._pair_rect = UiRect(gap, y, half_w, btn_h)
    self._connect_rect = UiRect(gap * 2 + half_w, y, half_w, btn_h)
    self._bottom_bar_top = y - 10

  def back_rect(self) -> UiRect:
    """Return the back-button hit rectangle."""
    return self._back_pad

  def pair_rect(self) -> UiRect:
    """Return the PAIR button hit rectangle."""
    return self._pair_rect

  def connect_rect(self) -> UiRect:
    """Return the CONNECT button hit rectangle."""
    return self._connect_rect

  def disconnect_rect(self) -> UiRect:
    """Return the DISC button hit rectangle."""
    return self._disconnect_rect

  def draw_overlay(
    self,
    img,
    connected: bool,
    busy: bool,
    state,
    drive,
    max_speed: int = 255,
    status: str = "",
    progress: float = 0.0,
  ) -> None:
    """Draw HUD: speed bar, sticks, triggers, d-pad, connection buttons."""
    bx = self._back_pad
    img.draw_rect(bx.x, bx.y, bx.width, bx.height, image.Color.from_rgb(0, 0, 0), thickness=-1)
    icon_x = bx.x + (bx.width - self._img_back.width()) // 2
    icon_y = bx.y + (bx.height - self._img_back.height()) // 2
    img.draw_image(icon_x, icon_y, self._img_back)

    if connected:
      self._draw_button(img, self.disconnect_rect(), "DISC", image.Color.from_rgb(180, 60, 40))
      lb = state.buttons.get(ControllerButton.LB, False)
      rb = state.buttons.get(ControllerButton.RB, False)
      self._draw_speed_bar(img, max_speed, lb, rb)

      gauge_cy = self.height // 2 + 8
      radius = min(68, (self.width - 120) // 4)
      bar_h = radius * 2 + 6
      bar_y = gauge_cy - bar_h // 2
      left_cx = self.width // 4 + 4
      right_cx = self.width - self.width // 4 - 4

      self._draw_gauge(img, left_cx, gauge_cy, state.left_x, state.left_y, radius=radius, label="L")
      self._draw_gauge(img, right_cx, gauge_cy, state.right_x, state.right_y, radius=radius, label="R")
      self._draw_trigger_bar(
        img, 6, bar_y, 26, bar_h, state.lt, "LT", image.Color.from_rgb(60, 120, 220),
      )
      self._draw_trigger_bar(
        img, self.width - 32, bar_y, 26, bar_h, state.rt, "RT",
        image.Color.from_rgb(220, 100, 60),
      )
      self._draw_dpad(img, self.width // 2, gauge_cy + radius + 28, state.dpad_x, state.dpad_y)
      self._draw_face_buttons(img, state)
    elif busy:
      self._draw_bottom_bar(img)
      self._draw_progress(img, status, progress)
      self._draw_button(img, self.pair_rect(), "...", image.Color.from_rgb(80, 80, 80))
      self._draw_button(img, self.connect_rect(), "...", image.Color.from_rgb(80, 80, 80))
    else:
      self._draw_bottom_bar(img)
      self._draw_button(img, self.pair_rect(), "PAIR", image.Color.from_rgb(40, 80, 160))
      self._draw_button(img, self.connect_rect(), "CONNECT", image.Color.from_rgb(40, 120, 60))

  def _draw_progress(self, img, status: str, progress: float) -> None:
    """Show pairing/connect status text and a simple progress bar."""
    pct = max(0.0, min(1.0, float(progress)))
    bar_x = 24
    bar_w = self.width - 48
    bar_y = self.height // 2 - 10
    bar_h = 18
    label = status or "Working..."
    size = image.string_size(label, scale=1.1, thickness=1)
    img.draw_string(
      (self.width - size.width()) // 2,
      bar_y - 28,
      label,
      image.COLOR_WHITE,
      scale=1.1,
    )
    img.draw_rect(bar_x, bar_y, bar_w, bar_h, image.Color.from_rgb(30, 30, 30), thickness=-1)
    img.draw_rect(bar_x, bar_y, bar_w, bar_h, image.COLOR_WHITE, thickness=1)
    fill = int((bar_w - 4) * pct)
    if fill > 0:
      img.draw_rect(
        bar_x + 2, bar_y + 2, fill, bar_h - 4,
        image.Color.from_rgb(60, 160, 220), thickness=-1,
      )

  def _draw_speed_bar(self, img, max_speed: int, lb_pressed: bool, rb_pressed: bool) -> None:
    y = 52
    x = 54
    w = self.width - 108
    h = self.SPEED_BAR_H
    pct = max(0, min(100, int(round(max_speed * 100 / 255))))

    img.draw_rect(x, y, w, h, image.Color.from_rgb(20, 20, 20), thickness=-1)
    img.draw_rect(x, y, w, h, image.COLOR_WHITE, thickness=1)
    fill_w = max(0, int(w * pct / 100))
    if fill_w > 0:
      img.draw_rect(x + 1, y + 1, fill_w - 2, h - 2, image.Color.from_rgb(40, 180, 90), thickness=-1)

    label = f"SPD {pct}%"
    size = image.string_size(label, scale=1.0, thickness=1)
    img.draw_string(x + (w - size.width()) // 2, y + 4, label, image.COLOR_WHITE, scale=1.0)

    lb_c = image.Color.from_rgb(80, 200, 100) if lb_pressed else image.Color.from_rgb(35, 35, 35)
    rb_c = image.Color.from_rgb(80, 200, 100) if rb_pressed else image.Color.from_rgb(35, 35, 35)
    img.draw_rect(x - 30, y + 2, 26, h - 4, lb_c, thickness=-1)
    img.draw_rect(x + w + 4, y + 2, 26, h - 4, rb_c, thickness=-1)
    img.draw_string(x - 26, y + 5, "LB", image.COLOR_WHITE, scale=0.85)
    img.draw_string(x + w + 8, y + 5, "RB", image.COLOR_WHITE, scale=0.85)

  def _draw_bottom_bar(self, img) -> None:
    y = self._bottom_bar_top
    img.draw_rect(0, y, self.width, self.height - y, image.Color.from_rgb(0, 0, 0), thickness=-1)

  def _draw_gauge(self, img, cx, cy, axis_x, axis_y, radius=72, label="") -> None:
    img.draw_circle(cx, cy, radius, image.Color.from_rgb(40, 40, 40), thickness=2)
    img.draw_circle(cx, cy, radius, image.Color.from_rgb(200, 200, 200), thickness=1)
    dx = int((axis_x / 32767.0) * (radius - 10))
    dy = int((axis_y / 32767.0) * (radius - 10))
    img.draw_circle(cx + dx, cy + dy, 10, image.Color.from_rgb(255, 140, 40), thickness=-1)
    if label:
      size = image.string_size(label, scale=1.0, thickness=1)
      img.draw_string(cx - size.width() // 2, cy - radius - 14, label, image.COLOR_WHITE, scale=1.0)

  def _draw_dpad(self, img, cx, cy, dx, dy) -> None:
    r = 7
    gap = 14
    dim = image.Color.from_rgb(30, 30, 30)
    on = image.Color.from_rgb(255, 180, 40)
    self._draw_dpad_dot(img, cx, cy - gap, r, dy < 0 and dx == 0, on, dim)
    self._draw_dpad_dot(img, cx, cy + gap, r, dy > 0 and dx == 0, on, dim)
    self._draw_dpad_dot(img, cx - gap, cy, r, dx < 0 and dy == 0, on, dim)
    self._draw_dpad_dot(img, cx + gap, cy, r, dx > 0 and dy == 0, on, dim)
    self._draw_dpad_dot(img, cx - gap, cy - gap, r, dy < 0 and dx < 0, on, dim)
    self._draw_dpad_dot(img, cx + gap, cy - gap, r, dy < 0 and dx > 0, on, dim)
    self._draw_dpad_dot(img, cx - gap, cy + gap, r, dy > 0 and dx < 0, on, dim)
    self._draw_dpad_dot(img, cx + gap, cy + gap, r, dy > 0 and dx > 0, on, dim)

  def _draw_dpad_dot(self, img, x, y, radius, active, on_color, dim_color) -> None:
    color = on_color if active else dim_color
    img.draw_circle(x, y, radius, color, thickness=-1)

  def _draw_face_buttons(self, img, state) -> None:
    """Highlight A/B/X/Y when pressed (bottom-right cluster)."""
    cx = self.width - 56
    cy = self.height - 110
    gap = 18
    r = 12
    dim = image.Color.from_rgb(35, 35, 35)
    on = image.Color.from_rgb(80, 200, 100)
    layout = (
      (cx, cy - gap, "Y", ControllerButton.Y),
      (cx, cy + gap, "A", ControllerButton.A),
      (cx - gap, cy, "X", ControllerButton.X),
      (cx + gap, cy, "B", ControllerButton.B),
    )
    for x, y, label, button in layout:
      pressed = state.buttons.get(button, False)
      color = on if pressed else dim
      img.draw_circle(x, y, r, color, thickness=-1)
      size = image.string_size(label, scale=0.85, thickness=1)
      img.draw_string(x - size.width() // 2, y - size.height() // 2, label, image.COLOR_WHITE, scale=0.85)

  def _draw_trigger_bar(self, img, x, y, w, h, value, label, color) -> None:
    img.draw_rect(x, y, w, h, image.Color.from_rgb(30, 30, 30), thickness=-1)
    img.draw_rect(x, y, w, h, image.COLOR_WHITE, thickness=1)
    mag = min(32767, abs(int(value)))
    fill_h = int((mag / 32767.0) * (h - 6))
    if fill_h > 0:
      fy = y + h - 3 - fill_h
      img.draw_rect(x + 3, fy, w - 6, fill_h, color, thickness=-1)
    size = image.string_size(label, scale=1.0, thickness=1)
    img.draw_string(x + (w - size.width()) // 2, y + h + 2, label, image.COLOR_WHITE, scale=1.0)

  def _draw_button(self, img, rect: UiRect, label: str, color) -> None:
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, color, thickness=-1)
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, image.COLOR_WHITE, thickness=2)
    size = image.string_size(label, scale=1.35, thickness=1)
    tx = rect.x + (rect.width - size.width()) // 2
    ty = rect.y + (rect.height - size.height()) // 2
    img.draw_string(tx, ty, label, image.COLOR_WHITE, scale=1.35)

  def _load_back_btn(self, width: int):
    img = image.load("/maixapp/share/icon/ret.png")
    w = 28
    h = img.height() * w // img.width()
    if w % 2:
      w += 1
    if h % 2:
      h += 1
    return img.resize(w, h)
