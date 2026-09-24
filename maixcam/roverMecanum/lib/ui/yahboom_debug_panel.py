"""Full-screen Yahboom debug menu: bat / IMU / encoders + smoke buttons."""

from __future__ import annotations

from maix import image

from lib.ui.hud_instruments import battery_pct
from lib.ui.ui_rect import UiRect
from lib.yahboom.yahboom_debug_snapshot import YahboomDebugSnapshot


class YahboomDebugPanel:
  """Opaque Yahboom DBG screen with live telemetry and four actions."""

  def __init__(self, width: int, height: int) -> None:
    self.width = width
    self.height = height
    btn_h = 56
    gap = 10
    y = height - btn_h * 2 - gap * 3 - 8
    half = (width - gap * 3) // 2
    self._btn_poll = UiRect(gap, y, half, btn_h)
    self._btn_stop = UiRect(gap * 2 + half, y, half, btn_h)
    y2 = y + btn_h + gap
    self._btn_fwd = UiRect(gap, y2, half, btn_h)
    self._btn_init = UiRect(gap * 2 + half, y2, half, btn_h)
    self._close_rect = UiRect(8, 8, 44, 44)

  def close_rect(self) -> UiRect:
    """Return the close/back hit rectangle."""
    return self._close_rect

  def poll_rect(self) -> UiRect:
    """Return the POLL button rectangle."""
    return self._btn_poll

  def stop_rect(self) -> UiRect:
    """Return the STOP button rectangle."""
    return self._btn_stop

  def fwd_rect(self) -> UiRect:
    """Return the FWD crawl button rectangle."""
    return self._btn_fwd

  def init_rect(self) -> UiRect:
    """Return the INIT (refresh auto-report) button rectangle."""
    return self._btn_init

  def draw(self, img, snap: YahboomDebugSnapshot) -> None:
    """Paint Yahboom DBG HUD from a snapshot."""
    img.draw_rect(0, 0, self.width, self.height, image.Color.from_rgb(10, 12, 18), thickness=-1)
    img.draw_rect(
      self._close_rect.x,
      self._close_rect.y,
      self._close_rect.width,
      self._close_rect.height,
      image.Color.from_rgb(30, 30, 35),
      thickness=-1,
    )
    img.draw_string(18, 16, "<", image.COLOR_WHITE, scale=1.4)

    title = "Yahboom Debug"
    title_scale = 1.5
    size = image.string_size(title, scale=title_scale, thickness=2)
    img.draw_string(
      (self.width - size.width()) // 2, 22, title, image.COLOR_WHITE, scale=title_scale,
    )

    y = 78
    muted = image.Color.from_rgb(160, 165, 175)
    img.draw_string(24, y, "link: CH340 USB", image.COLOR_WHITE, scale=1.15)
    y += 34
    img.draw_string(24, y, (snap.status or "—")[:42], muted, scale=1.0)
    y += 40
    for line in self._lines(snap):
      img.draw_string(24, y, line, image.COLOR_WHITE, scale=1.05)
      y += 28
      if y > self._btn_poll.y - 16:
        break

    self._draw_btn(img, self._btn_poll, "POLL", image.Color.from_rgb(40, 90, 160))
    self._draw_btn(img, self._btn_stop, "STOP", image.Color.from_rgb(160, 50, 40))
    self._draw_btn(img, self._btn_fwd, "FWD", image.Color.from_rgb(40, 120, 70))
    self._draw_btn(img, self._btn_init, "INIT", image.Color.from_rgb(90, 70, 140))

  def _lines(self, snap: YahboomDebugSnapshot) -> list[str]:
    bat = snap.battery
    if bat is None:
      lines = ["bat —"]
    else:
      pct = battery_pct(bat.millivolts)
      lines = [f"bat {pct}%  {bat.volts:.2f} V"]
    imu = snap.imu
    if imu is None:
      lines.append("imu —")
    else:
      lines.append(f"yaw {imu.yaw_deg:.0f}")
      lines.append(f"att P{imu.pitch_deg:+.0f} R{imu.roll_deg:+.0f}")
    enc = snap.encoders
    lines.append(f"enc FL/FR {enc.m1} / {enc.m2}")
    lines.append(f"enc RL/RR {enc.m3} / {enc.m4}")
    return lines

  def _draw_btn(self, img, rect: UiRect, label: str, color) -> None:
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, color, thickness=-1)
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, image.COLOR_WHITE, thickness=2)
    size = image.string_size(label, scale=1.25, thickness=1)
    img.draw_string(
      rect.x + (rect.width - size.width()) // 2,
      rect.y + (rect.height - size.height()) // 2,
      label,
      image.COLOR_WHITE,
      scale=1.25,
    )
