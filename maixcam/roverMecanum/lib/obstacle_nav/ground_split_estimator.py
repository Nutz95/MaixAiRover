"""Propose ground_top_ratio on the light-green turbo band (not orange)."""

from lib.vision.depth_pixel import pixel_rgb


class GroundSplitEstimator:
  """Find the light-green floor/horizon wash under a tilted camera."""

  def propose(
    self,
    depth_img,
    *,
    frame_width: int,
    frame_height: int,
    floor_warmth: float = 0.08,
    min_ratio: float = 0.35,
    max_ratio: float = 0.75,
  ) -> float | None:
    """Return Y ratio of the greener row in-range (skips red/orange floor)."""
    if depth_img is None or frame_width <= 0 or frame_height <= 0:
      return None
    dw = max(1, depth_img.width())
    dh = max(1, depth_img.height())
    scale_x = dw / frame_width
    scale_y = dh / frame_height
    x0 = int(frame_width * 0.35)
    x1 = int(frame_width * 0.65)
    y_lo = int(frame_height * max_ratio)
    y_hi = int(frame_height * min_ratio)
    if y_lo <= y_hi:
      return None
    step = max(1, frame_height // 50)
    best_y = None
    best_green = -1e9
    # Reject rows still in the warm (orange/red) floor wash.
    warm_cap = max(floor_warmth + 0.12, 0.20)
    for y in range(y_hi, y_lo + 1, step):
      green, warmth = self._row_green_warmth(
        depth_img, x0, x1, y, scale_x, scale_y,
      )
      if warmth > warm_cap:
        continue
      if green > best_green:
        best_green = green
        best_y = y
    if best_y is None or best_green < 8.0:
      return None
    ratio = best_y / float(frame_height)
    return max(min_ratio, min(max_ratio, ratio))

  @staticmethod
  def _row_green_warmth(
    depth_img, x0: int, x1: int, y: int, scale_x: float, scale_y: float,
  ):
    """Mean turbo green-ness G−(R+B)/2 and warmth (R−B)/255 for one row."""
    total_g = 0.0
    total_w = 0.0
    count = 0
    step = max(1, (x1 - x0) // 8)
    dy = int(y * scale_y)
    for x in range(x0, x1, step):
      rgb = pixel_rgb(depth_img, int(x * scale_x), dy)
      if rgb is None:
        continue
      r, g, b = rgb
      total_g += g - (r + b) * 0.5
      total_w += (r - b) / 255.0
      count += 1
    if count <= 0:
      return 0.0, 0.0
    return total_g / count, total_w / count
