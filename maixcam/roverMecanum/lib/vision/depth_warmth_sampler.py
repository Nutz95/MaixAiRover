"""Sample turbo warmth and map ball / ROI near cues."""

from __future__ import annotations

from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_observation import BallObservation
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.vision.ball_depth_band import BallDepthBand
from lib.vision.depth_pixel import pixel_warmth


class DepthWarmthSampler:
  """Shared (R−B)/255 warmth helpers for ball band + near LED."""

  def classify_ball(
    self,
    depth_img,
    observation: BallObservation | None,
    settings: BallFollowSettings,
  ) -> BallDepthBand:
    """Map turbo warmth at the ball centre (+ size hint) to a distance band."""
    if observation is None:
      return BallDepthBand.UNKNOWN
    try:
      scale_x = depth_img.width() / max(1, observation.image_width)
      scale_y = depth_img.height() / max(1, observation.image_height)
      x = int(observation.center_x * scale_x)
      y = int(observation.center_y * scale_y)
      warmth = self.sample(depth_img, x, y)
      band = self.band_from_warmth(warmth, settings)
      height = observation.height_ratio
      if height >= settings.too_close_height_ratio and band is not BallDepthBand.CLOSE:
        return BallDepthBand.CLOSE
      if height < settings.target_height_ratio * 0.55 and band is BallDepthBand.OK:
        return BallDepthBand.FAR
      return band
    except Exception as band_error:
      print(f"depth: ball band: {band_error}")
      return BallDepthBand.UNKNOWN

  def estimate_near(
    self,
    depth_img,
    observation: BallObservation | None,
    settings: BallFollowSettings,
    nav_roi: NavRoiLayout | None,
    target_w: int,
    target_h: int,
  ) -> bool:
    """ROI ahead looks close (warm) while ball is absent/far in that band."""
    try:
      w = depth_img.width()
      h = depth_img.height()
      if nav_roi is not None:
        full_w = max(1, target_w) if target_w > 0 else w
        full_h = max(1, target_h) if target_h > 0 else h
        box = nav_roi.obstacle_box(full_w, full_h)
        left = int(box.left * w / full_w)
        right = int(box.right * w / full_w)
        top = int(box.top * h / full_h)
        bottom = int(box.bottom * h / full_h)
      else:
        left = int(settings.depth_roi_left_ratio * w)
        right = int(settings.depth_roi_right_ratio * w)
        top = int(settings.depth_roi_top_ratio * h)
        bottom = int(settings.depth_roi_bottom_ratio * h)
      if right <= left or bottom <= top:
        return False
      total = 0.0
      count = 0
      step_x = max(1, (right - left) // 8)
      step_y = max(1, (bottom - top) // 8)
      for y in range(top, bottom, step_y):
        for x in range(left, right, step_x):
          total += self.sample(depth_img, x, y)
          count += 1
      if count <= 0:
        return False
      mean_warmth = total / count
      ball_blocking = (
        observation is not None
        and observation.height_ratio >= settings.too_close_height_ratio * 0.7
      )
      return mean_warmth >= settings.depth_close_warmth and not ball_blocking
    except Exception as near_error:
      print(f"depth: near estimate: {near_error}")
      return False

  @staticmethod
  def band_from_warmth(warmth: float, settings: BallFollowSettings) -> BallDepthBand:
    """Map a warmth sample to CLOSE / OK / FAR."""
    if warmth >= settings.depth_close_warmth:
      return BallDepthBand.CLOSE
    if warmth <= settings.depth_far_warmth:
      return BallDepthBand.FAR
    return BallDepthBand.OK

  @staticmethod
  def sample(depth_img, cx: int, cy: int) -> float:
    """Average (R−B)/255 in a small window — turbo warm = near."""
    total = 0.0
    count = 0
    for dy in (-2, 0, 2):
      for dx in (-2, 0, 2):
        total += pixel_warmth(depth_img, cx + dx, cy + dy)
        count += 1
    return total / count if count else 0.0
