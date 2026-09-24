"""Full-screen HUD overlay for camera + controller state."""

import math

from maix import image

from lib.input.controller_button import ControllerButton
from lib.ui.hud_instruments import HudInstruments
from lib.ui.ui_rect import UiRect


class UiDrawer:
  """Full-screen HUD overlay (portrait) for camera + controller state."""

  SPEED_BAR_H = 20
  BATTERY_BAR_H = 18
  TOP_PAD = 6

  def __init__(self, width: int, height: int) -> None:
    self.width = width
    self.height = height
    self._img_back = self._load_back_btn(width)
    self._layout_buttons()

  def _top_battery_y(self) -> int:
    return self.TOP_PAD

  def _top_speed_y(self) -> int:
    return self.TOP_PAD + self.BATTERY_BAR_H + 2

  def _layout_buttons(self) -> None:
    pad = 8
    back_size = 44
    self._back_pad = UiRect(pad, pad, back_size, back_size)
    btn_h = 72
    gap = 12
    y = self.height - btn_h - 10
    half_w = (self.width - gap * 3) // 2
    left = UiRect(gap, y, half_w, btn_h)
    right = UiRect(gap * 2 + half_w, y, half_w, btn_h)
    self._pair_rect = left
    self._disconnect_rect = left
    self._connect_rect = right
    self._debug_rect = right
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

  def debug_rect(self) -> UiRect:
    """Return the DBG button hit rectangle."""
    return self._debug_rect

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
    instruments: HudInstruments | None = None,
    wheel_fl: int = 0,
    wheel_fr: int = 0,
    motor_limit: int = 50,
  ) -> None:
    """Draw HUD: speed bar, instruments, sticks, connection buttons."""
    bx = self._back_pad
    img.draw_rect(bx.x, bx.y, bx.width, bx.height, image.Color.from_rgb(0, 0, 0), thickness=-1)
    icon_x = bx.x + (bx.width - self._img_back.width()) // 2
    icon_y = bx.y + (bx.height - self._img_back.height()) // 2
    img.draw_image(icon_x, icon_y, self._img_back)

    if connected:
      self._draw_bottom_bar(img)
      self._draw_button(img, self.disconnect_rect(), "DISC", image.Color.from_rgb(180, 60, 40))
      self._draw_button(img, self.debug_rect(), "DBG", image.Color.from_rgb(50, 90, 140))
      lb = state.buttons.get(ControllerButton.LB, False)
      rb = state.buttons.get(ControllerButton.RB, False)
      self._draw_speed_bar(img, max_speed, lb, rb, wheel_fl, wheel_fr, motor_limit)
      self._draw_instruments(img, instruments)

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

  def _draw_instruments(self, img, instruments: HudInstruments | None) -> None:
    """Heading under speed bar + dual battery + mini pitch/roll."""
    y = self._top_speed_y() + self.SPEED_BAR_H + 4
    if instruments is None:
      instruments = HudInstruments(None, None, None, None, None, None, None)
    if instruments.cardinal is not None and instruments.heading_deg is not None:
      label = f"{instruments.cardinal}  {instruments.heading_deg:05.1f}"
    else:
      label = "CAP —"
    size = image.string_size(label, scale=1.15, thickness=1)
    img.draw_string(
      (self.width - size.width()) // 2, y, label, image.COLOR_WHITE, scale=1.15,
    )
    self._draw_battery_bar(
      img,
      instruments.maix_battery_pct,
      instruments.battery_pct,
    )
    self._draw_attitude(img, instruments.pitch_deg, instruments.roll_deg)

  def _battery_color(self, pct: int | None):
    """Green→yellow→red by SoC percent."""
    if pct is None:
      return image.Color.from_rgb(80, 80, 80)
    if pct <= 20:
      return image.Color.from_rgb(200, 60, 40)
    if pct <= 40:
      return image.Color.from_rgb(200, 160, 40)
    return image.Color.from_rgb(40, 180, 90)

  def _draw_battery_bar(
    self,
    img,
    maix_pct: int | None,
    rover_pct: int | None,
  ) -> None:
    """Two half-bars: CAM fills left from center, ROV fills right from center."""
    x = 54
    y = self._top_battery_y()
    w = self.width - 108
    h = self.BATTERY_BAR_H
    mid = x + w // 2
    half = w // 2
    img.draw_rect(x, y, w, h, image.Color.from_rgb(20, 20, 20), thickness=-1)
    img.draw_rect(x, y, w, h, image.COLOR_WHITE, thickness=1)
    img.draw_line(mid, y, mid, y + h, image.Color.from_rgb(90, 90, 90), thickness=1)

    cam_fill = 0 if maix_pct is None else max(0, min(half - 2, int(half * maix_pct / 100)))
    rov_fill = 0 if rover_pct is None else max(0, min(half - 2, int(half * rover_pct / 100)))
    if cam_fill > 1:
      img.draw_rect(
        mid - cam_fill, y + 1, cam_fill, h - 2,
        self._battery_color(maix_pct), thickness=-1,
      )
    if rov_fill > 1:
      img.draw_rect(
        mid + 1, y + 1, rov_fill, h - 2,
        self._battery_color(rover_pct), thickness=-1,
      )

    cam = "—" if maix_pct is None else f"{maix_pct}%"
    rov = "—" if rover_pct is None else f"{rover_pct}%"
    left = f"CAM {cam}"
    right = f"ROV {rov}"
    ls = image.string_size(left, scale=0.8, thickness=1)
    rs = image.string_size(right, scale=0.8, thickness=1)
    img.draw_string(x + 4, y + 2, left, image.COLOR_WHITE, scale=0.8)
    img.draw_string(x + w - rs.width() - 4, y + 2, right, image.COLOR_WHITE, scale=0.8)
    del ls

  def _draw_attitude(self, img, pitch: float | None, roll: float | None) -> None:
    """Small artificial-horizon style pitch/roll strip near top-right."""
    cx = self.width - 52
    cy = self._top_speed_y() + self.SPEED_BAR_H + 48
    r = 28
    img.draw_circle(cx, cy, r, image.Color.from_rgb(30, 40, 55), thickness=-1)
    img.draw_circle(cx, cy, r, image.COLOR_WHITE, thickness=1)
    if pitch is None or roll is None:
      img.draw_string(cx - 10, cy - 6, "—", image.COLOR_WHITE, scale=1.0)
      return
    pr = max(-30.0, min(30.0, pitch))
    rr = max(-45.0, min(45.0, roll))
    rad = math.radians(rr)
    dy = int((-pr / 30.0) * (r - 6))
    dx = int(math.cos(rad) * (r - 4))
    dy_line = int(math.sin(rad) * (r - 4))
    img.draw_line(
      cx - dx, cy + dy - dy_line, cx + dx, cy + dy + dy_line,
      image.Color.from_rgb(80, 200, 120), thickness=2,
    )
    img.draw_line(cx - 6, cy, cx + 6, cy, image.Color.from_rgb(255, 200, 40), thickness=1)
    img.draw_string(cx - r, cy + r + 4, f"P{pitch:+.0f}", image.COLOR_WHITE, scale=0.75)
    img.draw_string(cx + 2, cy + r + 4, f"R{roll:+.0f}", image.COLOR_WHITE, scale=0.75)

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

  def _draw_speed_bar(
    self,
    img,
    max_speed: int,
    lb_pressed: bool,
    rb_pressed: bool,
    wheel_fl: int = 0,
    wheel_fr: int = 0,
    motor_limit: int = 50,
  ) -> None:
    y = self._top_speed_y()
    x = 54
    w = self.width - 108
    h = self.SPEED_BAR_H
    pct = max(0, min(100, int(round(max_speed * 100 / 255))))
    del motor_limit

    img.draw_rect(x, y, w, h, image.Color.from_rgb(20, 20, 20), thickness=-1)
    img.draw_rect(x, y, w, h, image.COLOR_WHITE, thickness=1)
    fill_w = max(0, int(w * pct / 100))
    # MaixPy draw_rect rejects non-positive sizes ("index out of range").
    if fill_w > 2:
      img.draw_rect(
        x + 1, y + 1, fill_w - 2, h - 2,
        image.Color.from_rgb(40, 180, 90), thickness=-1,
      )

    label = f"SPD {pct}%  FL/FR {wheel_fl}/{wheel_fr}"
    size = image.string_size(label, scale=0.85, thickness=1)
    img.draw_string(x + (w - size.width()) // 2, y + 3, label, image.COLOR_WHITE, scale=0.85)

    lb_c = image.Color.from_rgb(80, 200, 100) if lb_pressed else image.Color.from_rgb(35, 35, 35)
    rb_c = image.Color.from_rgb(80, 200, 100) if rb_pressed else image.Color.from_rgb(35, 35, 35)
    img.draw_rect(x - 30, y + 2, 26, h - 4, lb_c, thickness=-1)
    img.draw_rect(x + w + 4, y + 2, 26, h - 4, rb_c, thickness=-1)
    img.draw_string(x - 26, y + 4, "LB", image.COLOR_WHITE, scale=0.85)
    img.draw_string(x + w + 8, y + 4, "RB", image.COLOR_WHITE, scale=0.85)

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
    """Highlight A/B/X/Y when pressed (above the bottom DISC/DBG bar)."""
    cx = self.width - 56
    cy = self._bottom_bar_top - 48
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
