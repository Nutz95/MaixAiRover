"""Sample turbo warmth in obstacle L/C/R thirds (ball-masked)."""

from __future__ import annotations

from lib.ball_follow.ball_observation import BallObservation
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.nav_roi_pixel_box import NavRoiPixelBox
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading
from lib.vision.depth_pixel import pixel_warmth


class ObstacleBandSampler:
  """Map full-frame ROI onto a possibly smaller depth plane and average warmth."""

  GRID_X = 6
  GRID_Y = 4

  def sample(
    self,
    depth_img,
    layout: NavRoiLayout,
    *,
    frame_width: int,
    frame_height: int,
    ball: BallObservation | None = None,
  ) -> ObstacleBandReading:
    """Return absolute L/C/R turbo warmth in the obstacle band (above ground)."""
    if depth_img is None or frame_width <= 0 or frame_height <= 0:
      return ObstacleBandReading.clear()
    box = layout.obstacle_box(frame_width, frame_height)
    if box.is_empty():
      return ObstacleBandReading.clear()
    dw = max(1, depth_img.width())
    dh = max(1, depth_img.height())
    scale_x = dw / frame_width
    scale_y = dh / frame_height
    ball_box = self._ball_box(ball, frame_width, frame_height)
    third = max(1, box.width // 3)
    return ObstacleBandReading(
      left=self._mean_third(
        depth_img, box, 0, third, scale_x, scale_y, ball_box,
      ),
      center=self._mean_third(
        depth_img, box, third, 2 * third, scale_x, scale_y, ball_box,
      ),
      right=self._mean_third(
        depth_img, box, 2 * third, box.width, scale_x, scale_y, ball_box,
      ),
    )

  def _mean_third(
    self,
    depth_img,
    box: NavRoiPixelBox,
    x0_off: int,
    x1_off: int,
    scale_x: float,
    scale_y: float,
    ball_box: NavRoiPixelBox | None,
  ) -> float:
    left = box.left + x0_off
    right = box.left + x1_off
    if right <= left or box.height <= 0:
      return 0.0
    cell_w = max(1, (right - left) // self.GRID_X)
    cell_h = max(1, box.height // self.GRID_Y)
    total = 0.0
    count = 0
    for row in range(self.GRID_Y):
      for col in range(self.GRID_X):
        cx = left + col * cell_w + cell_w // 2
        cy = box.top + row * cell_h + cell_h // 2
        if cx >= right or cy >= box.bottom:
          continue
        if ball_box is not None and self._inside(cx, cy, ball_box):
          continue
        total += pixel_warmth(depth_img, int(cx * scale_x), int(cy * scale_y))
        count += 1
    return total / count if count else 0.0

  @staticmethod
  def warmth_at(depth_img, x: int, y: int) -> float:
    """Turbo colormap warmth (R−B)/255."""
    return pixel_warmth(depth_img, x, y)

  @staticmethod
  def _ball_box(
    ball: BallObservation | None, frame_width: int, frame_height: int,
  ) -> NavRoiPixelBox | None:
    if ball is None:
      return None
    # Map detector image coords onto the HUD/frame size.
    sx = frame_width / max(1, ball.image_width)
    sy = frame_height / max(1, ball.image_height)
    half_w = max(1, int(ball.width * sx * 0.6))
    half_h = max(1, int(ball.height * sy * 0.6))
    cx = int(ball.center_x * sx)
    cy = int(ball.center_y * sy)
    return NavRoiPixelBox(
      left=max(0, cx - half_w),
      top=max(0, cy - half_h),
      right=min(frame_width, cx + half_w),
      bottom=min(frame_height, cy + half_h),
    )

  @staticmethod
  def _inside(x: int, y: int, box: NavRoiPixelBox) -> bool:
    return box.left <= x < box.right and box.top <= y < box.bottom
