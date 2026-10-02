"""Sample turbo warmth in obstacle columns (ball-masked)."""

from __future__ import annotations

from lib.ball_follow.ball_observation import BallObservation
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout
from lib.obstacle_nav.nav_roi_pixel_box import NavRoiPixelBox
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading
from lib.vision.depth_pixel import pixel_warmth


class ObstacleBandSampler:
  """Map full-frame ROI onto a depth plane; top-k mean warmth per column.

  Mean alone was too timid at edges; raw peak was twitchy on single hot pixels.
  Top-k mean sits in between. Column count comes from settings via the layout.
  """

  GRID_X = 4
  GRID_Y = 5
  # ponytail: k=3; raise toward mean (larger k) or lower toward peak (k=1).
  TOP_K = 3

  def sample(
    self,
    depth_img,
    layout: NavRoiLayout,
    *,
    frame_width: int,
    frame_height: int,
    column_count: int,
    ball: BallObservation | None = None,
  ) -> ObstacleBandReading:
    """Return per-column turbo warmth across the obstacle band."""
    count = max(1, int(column_count))
    if depth_img is None or frame_width <= 0 or frame_height <= 0:
      return ObstacleBandReading.clear(count)
    box = layout.obstacle_box(frame_width, frame_height)
    if box.is_empty():
      return ObstacleBandReading.clear(count)
    depth_width = max(1, depth_img.width())
    depth_height = max(1, depth_img.height())
    scale_x = depth_width / frame_width
    scale_y = depth_height / frame_height
    ball_box = self._ball_box(ball, frame_width, frame_height)
    warmths: list[float] = []
    for index in range(count):
      x0 = (box.width * index) // count
      x1 = (box.width * (index + 1)) // count
      warmths.append(
        self._hot_slice(
          depth_img, box, x0, x1, scale_x, scale_y, ball_box,
        ),
      )
    return ObstacleBandReading(columns=warmths)

  def _hot_slice(
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
    warmths: list[float] = []
    for row in range(self.GRID_Y):
      for col in range(self.GRID_X):
        sample_x = left + col * cell_w + cell_w // 2
        sample_y = box.top + row * cell_h + cell_h // 2
        if sample_x >= right or sample_y >= box.bottom:
          continue
        if ball_box is not None and self._inside(sample_x, sample_y, ball_box):
          continue
        warmths.append(
          pixel_warmth(
            depth_img, int(sample_x * scale_x), int(sample_y * scale_y),
          ),
        )
    if not warmths:
      return 0.0
    warmths.sort(reverse=True)
    take = min(self.TOP_K, len(warmths))
    return sum(warmths[:take]) / take

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
    scale_x = frame_width / max(1, ball.image_width)
    scale_y = frame_height / max(1, ball.image_height)
    half_w = max(1, int(ball.width * scale_x * 0.6))
    half_h = max(1, int(ball.height * scale_y * 0.6))
    center_x = int(ball.center_x * scale_x)
    center_y = int(ball.center_y * scale_y)
    return NavRoiPixelBox(
      left=max(0, center_x - half_w),
      top=max(0, center_y - half_h),
      right=min(frame_width, center_x + half_w),
      bottom=min(frame_height, center_y + half_h),
    )

  @staticmethod
  def _inside(x: int, y: int, box: NavRoiPixelBox) -> bool:
    return box.left <= x < box.right and box.top <= y < box.bottom
