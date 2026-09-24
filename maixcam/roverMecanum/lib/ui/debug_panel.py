"""Full-screen ESP debug menu with binary command buttons + live telem."""

from __future__ import annotations

from maix import image

from lib.esp.telem_snapshot import TelemSnapshot
from lib.ui.hud_instruments import from_telem
from lib.ui.ui_rect import UiRect


class DebugPanel:
  """Opaque debug screen: link status, telem lines, command buttons."""

  POLL_MS = 80

  def __init__(self, width: int, height: int) -> None:
    self.width = width
    self.height = height
    btn_h = 56
    gap = 10
    y = height - btn_h * 2 - gap * 3 - 8
    half = (width - gap * 3) // 2
    self._btn_ping = UiRect(gap, y, half, btn_h)
    self._btn_stop = UiRect(gap * 2 + half, y, half, btn_h)
    y2 = y + btn_h + gap
    self._btn_fwd = UiRect(gap, y2, half, btn_h)
    self._btn_init = UiRect(gap * 2 + half, y2, half, btn_h)
    self._close_rect = UiRect(8, 8, 44, 44)

  def close_rect(self) -> UiRect:
    """Return the close/back hit rectangle."""
    return self._close_rect

  def ping_rect(self) -> UiRect:
    """Return the PING button rectangle."""
    return self._btn_ping

  def stop_rect(self) -> UiRect:
    """Return the STOP button rectangle."""
    return self._btn_stop

  def fwd_rect(self) -> UiRect:
    """Return the FWD (SPEED 20 20) button rectangle."""
    return self._btn_fwd

  def init_rect(self) -> UiRect:
    """Return the INIT button rectangle."""
    return self._btn_init

  def draw(
    self,
    img,
    *,
    link_name: str,
    status: str,
    telem: TelemSnapshot | None,
  ) -> None:
    """Paint debug HUD."""
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

    title = "ESP Debug"
    title_scale = 1.5
    size = image.string_size(title, scale=title_scale, thickness=2)
    img.draw_string(
      (self.width - size.width()) // 2,
      22,
      title,
      image.COLOR_WHITE,
      scale=title_scale,
    )

    y = 78
    muted = image.Color.from_rgb(160, 165, 175)
    img.draw_string(24, y, f"link: {link_name or '—'}", image.COLOR_WHITE, scale=1.15)
    y += 34
    img.draw_string(24, y, status[:42], muted, scale=1.0)
    y += 40

    if telem is None:
      img.draw_string(24, y, "telem: waiting…", muted, scale=1.1)
    else:
      for line in self._telem_lines(telem):
        img.draw_string(24, y, line, image.COLOR_WHITE, scale=1.05)
        y += 28
        if y > self._btn_ping.y - 16:
          break

    self._draw_btn(img, self._btn_ping, "PING", image.Color.from_rgb(40, 90, 160))
    self._draw_btn(img, self._btn_stop, "STOP", image.Color.from_rgb(160, 50, 40))
    self._draw_btn(img, self._btn_fwd, "FWD 20", image.Color.from_rgb(40, 120, 70))
    self._draw_btn(img, self._btn_init, "INIT", image.Color.from_rgb(90, 70, 140))

  def _telem_lines(self, t: TelemSnapshot) -> list[str]:
    inst = from_telem(t)
    lines = [
      f"enc FL/FR {t.enc_fl} / {t.enc_fr}",
    ]
    if t.has_ina and inst.battery_pct is not None:
      lines.append(f"bat {inst.battery_pct}%  {t.bus_mv} mV  {t.current_ma} mA")
    elif t.has_ina:
      lines.append(f"bat {t.bus_mv} mV  {t.current_ma} mA")
    else:
      lines.append("bat — (no INA219)")
    if inst.cardinal is not None and inst.heading_deg is not None:
      lines.append(f"cap {inst.cardinal} {inst.heading_deg:.1f}")
    if t.has_imu:
      lines.append(f"acc {t.ax} {t.ay} {t.az}")
      lines.append(f"gyr {t.gx} {t.gy} {t.gz}")
      if inst.pitch_deg is not None and inst.roll_deg is not None:
        lines.append(f"att P{inst.pitch_deg:+.0f} R{inst.roll_deg:+.0f}")
      lines.append(f"temp {t.temp_c:.1f} C")
    else:
      lines.append("imu —")
    if t.has_mag:
      lines.append(f"mag {t.mx} {t.my} {t.mz}")
    else:
      lines.append("mag —")
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
