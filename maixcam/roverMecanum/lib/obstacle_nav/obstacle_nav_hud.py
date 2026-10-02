"""HUD paint helpers for ground calib + avoidance arrow."""

from __future__ import annotations

from lib.obstacle_nav.avoidance_arrow_panel import AvoidanceArrowPanel
from lib.obstacle_nav.avoidance_hint import AvoidanceHint
from lib.obstacle_nav.depth_ground_calib import DepthGroundCalib
from lib.obstacle_nav.nav_roi_guide_panel import NavRoiGuidePanel
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading
from lib.obstacle_nav.obstacle_near_mask_panel import ObstacleNearMaskPanel
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings

try:
  from maix import image as maix_image
except Exception as maix_import_error:
  print(f"obstacle hud: maix unavailable: {maix_import_error}")
  maix_image = None


class ObstacleNavHud:
  """Paint ROI guides, proposed ground line, prompt, and dodge arrow."""

  def __init__(self) -> None:
    """Create guide + arrow + zone panels."""
    self._roi = NavRoiGuidePanel()
    self._arrow = AvoidanceArrowPanel()
    self._zones = ObstacleNearMaskPanel()

  def draw_roi(
    self,
    frame,
    layout: NavRoiLayout,
    ground: DepthGroundCalib,
    *,
    show_guides: bool,
  ) -> None:
    """Paint green ground line and amber propose line during calib."""
    if show_guides:
      self._roi.draw(frame, layout)
    ratio = ground.proposed_ratio()
    if ground.is_active() and ratio is not None and maix_image is not None:
      y = int(ratio * frame.height())
      frame.draw_line(
        0, y, frame.width(), y, maix_image.Color.from_rgb(255, 180, 40), thickness=3,
      )

  def draw_status(
    self,
    frame,
    ground: DepthGroundCalib,
    hint: AvoidanceHint,
    reading: ObstacleBandReading,
    layout: NavRoiLayout,
    settings: ObstacleNavSettings,
    *,
    avoidance_enabled: bool,
  ) -> None:
    """Paint ground-calib prompt, persisted L/C/R zones, and dodge vector."""
    if ground.is_active():
      text = ground.prompt()
      if text and maix_image is not None:
        frame.draw_string(12, 8, text, maix_image.COLOR_WHITE, scale=1.6)
      return
    # Zones always (last depth reading) — do not wait for avoidance arm.
    self._zones.draw_from_reading(
      frame,
      layout,
      reading,
      close_warmth=settings.avoidance_close_warmth,
      caution_warmth=settings.avoidance_caution_warmth,
    )
    if maix_image is not None:
      frame.draw_string(
        8,
        frame.height() - 28,
        f"OBS L{reading.left:.2f} C{reading.center:.2f} R{reading.right:.2f}",
        maix_image.COLOR_WHITE,
        scale=1.3,
      )
    if not avoidance_enabled:
      return
    self._arrow.draw_vector(frame, reading)
    self._arrow.draw(frame, hint)
