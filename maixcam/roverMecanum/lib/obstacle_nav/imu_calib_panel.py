"""Full-screen IMU calibration wizard panel."""

from maix import image

from lib.obstacle_nav.imu_calib_snapshot import ImuCalibSnapshot
from lib.ui.ui_rect import UiRect


class ImuCalibPanel:
  """Opaque calib screen with Confirm / Skip and live attitude."""

  def __init__(self, width: int, height: int) -> None:
    """Layout primary buttons above the HUD chrome row."""
    self.width = width
    self.height = height
    btn_h = 72
    gap = 16
    self._ok_rect = UiRect(gap, height - btn_h - 100, width - gap * 2 - 150, btn_h)
    self._skip_rect = UiRect(
      self._ok_rect.x + self._ok_rect.width + gap,
      self._ok_rect.y,
      134,
      btn_h,
    )

  def ok_rect(self) -> UiRect:
    """Return the Confirm button hit rectangle."""
    return self._ok_rect

  def skip_rect(self) -> UiRect:
    """Return the Skip button hit rectangle."""
    return self._skip_rect

  def draw(self, img, snap: ImuCalibSnapshot) -> None:
    """Paint step title, attitude readouts, and action buttons."""
    img.draw_rect(0, 0, self.width, self.height, image.Color.from_rgb(12, 14, 20), thickness=-1)
    img.draw_string(20, 18, snap.title, image.COLOR_WHITE, scale=2.4)
    self._draw_wrapped(
      img, 20, 70, snap.detail, image.Color.from_rgb(200, 205, 215), scale=1.6,
    )
    bar_w = self.width - 40
    filled = int(bar_w * max(0.0, min(1.0, snap.progress_ratio)))
    img.draw_rect(20, 150, bar_w, 14, image.Color.from_rgb(40, 44, 52), thickness=-1)
    if filled > 0:
      img.draw_rect(20, 150, filled, 14, image.Color.from_rgb(240, 150, 60), thickness=-1)

    y = 180
    img.draw_string(
      20, y,
      f"PITCH {snap.pitch_deg:+.1f}",
      image.COLOR_WHITE,
      scale=2.0,
    )
    img.draw_string(
      20, y + 44,
      f"ROLL  {snap.roll_deg:+.1f}",
      image.COLOR_WHITE,
      scale=2.0,
    )
    img.draw_string(
      20, y + 88,
      f"YAW   {snap.yaw_deg:+.1f}",
      image.COLOR_WHITE,
      scale=2.0,
    )
    img.draw_string(
      20, y + 140,
      "Press A or OK",
      image.Color.from_rgb(240, 180, 90),
      scale=1.7,
    )
    self._draw_button(img, self._ok_rect, "OK / A", enabled=snap.can_confirm, accent=True)
    self._draw_button(img, self._skip_rect, "Skip", enabled=snap.can_skip, accent=False)

  def _draw_wrapped(self, img, x: int, y: int, text: str, color, *, scale: float) -> None:
    max_chars = max(12, int(self.width / (11 * scale)))
    line = text
    row = y
    while line:
      chunk = line[:max_chars]
      img.draw_string(x, row, chunk, color, scale=scale)
      line = line[max_chars:]
      row += int(28 * scale / 1.6)
      if row > 140:
        break

  def _draw_button(self, img, rect: UiRect, label: str, *, enabled: bool, accent: bool) -> None:
    if not enabled:
      color = image.Color.from_rgb(50, 50, 55)
    elif accent:
      color = image.Color.from_rgb(40, 140, 70)
    else:
      color = image.Color.from_rgb(70, 74, 82)
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, color, thickness=-1)
    img.draw_rect(rect.x, rect.y, rect.width, rect.height, image.COLOR_WHITE, thickness=2)
    size = image.string_size(label, scale=1.6, thickness=1)
    img.draw_string(
      rect.x + (rect.width - size.width()) // 2,
      rect.y + (rect.height - size.height()) // 2,
      label,
      image.COLOR_WHITE,
      scale=1.6,
    )
