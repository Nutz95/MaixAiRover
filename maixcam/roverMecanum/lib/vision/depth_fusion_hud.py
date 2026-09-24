"""DepthAnything V2 fusion — async infer, HUD paint on the camera thread."""

from __future__ import annotations

from time import monotonic

from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_follow_snapshot import BallFollowSnapshot
from lib.ball_follow.ball_observation import BallObservation
from lib.vision.ball_depth_band import BallDepthBand
from lib.vision.depth_infer_result import DepthInferResult
from lib.vision.depth_infer_worker import DepthInferWorker
from lib.vision.depth_view_mode import DepthViewMode

try:
  from maix import image as maix_image
  from maix import nn as maix_nn
except Exception as _maix_import_error:
  print(f"depth: maix unavailable: {_maix_import_error}")
  maix_image = None
  maix_nn = None

# Model native is ~322×238; infer small, upscale only when painting depth/blend.
_INFER_MAX_W = 320
_INFER_MAX_H = 240
_TIMING_LOG_MS = 2000


class DepthFusionHud:
  """DepthAnything for ball distance + optional HUD paint.

  Inference runs on a background worker so a 100–200 ms NN pass cannot stall
  the HUD. ``depth_view``: ``blend`` / ``depth`` / ``rgb``.
  """

  def __init__(self, settings: BallFollowSettings) -> None:
    """Defer NN load until first draw (camera buffers already allocated)."""
    self._settings = settings
    self._model = None
    self._last_submit_ms = 0
    self._last_depth = None
    self._last_band = BallDepthBand.UNKNOWN
    self._near_obstacle = False
    self._error = ""
    self._oom_disabled = False
    self._contours_disabled = False
    self._last_infer_ms = 0.0
    self._last_paint_ms = 0.0
    self._last_timing_log_ms = 0
    self._target_w = 0
    self._target_h = 0
    self._worker = DepthInferWorker(self._job)

  def apply_settings(self, settings: BallFollowSettings) -> None:
    """Hot-reload fusion flags; drop the NN when fusion is turned off."""
    old_path = self._settings.depth_model_path
    self._settings = settings
    if not settings.depth_fusion_enabled or self._oom_disabled:
      self._unload("off")
      return
    if self._model is not None and settings.depth_model_path != old_path:
      self._model = None
      self._last_depth = None

  def draw(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    """Paint last depth result; submit a new async job when due."""
    if not self._settings.depth_fusion_enabled or maix_image is None:
      return
    if self._oom_disabled:
      if self._error:
        img.draw_string(
          8, 110, f"DEPTH OOM {self._error[:20]}", maix_image.COLOR_WHITE, scale=1.0,
        )
      return
    try:
      if self._model is None:
        self._try_load(self._settings.depth_model_path)
      if self._model is None:
        if self._error:
          img.draw_string(
            8, 110, f"DEPTH {self._error[:28]}", maix_image.COLOR_WHITE, scale=1.0,
          )
        return
      self._consume_result()
      now_ms = int(monotonic() * 1000)
      self._maybe_submit(img, ball_snapshot, now_ms)
      paint_t0 = monotonic()
      self._paint(img)
      self._last_paint_ms = (monotonic() - paint_t0) * 1000.0
      if self._settings.depth_show_contours and not self._contours_disabled:
        if self._settings.depth_view is not DepthViewMode.RGB:
          self._draw_contours_low_res(img)
      if self._near_obstacle:
        self._draw_near_led(img)
      if self._settings.depth_ball_band_enabled:
        self._draw_ball_band(img, ball_snapshot)
      self._maybe_log_timing(now_ms)
    except MemoryError as oom:
      self._kill_after_oom(oom)
    except Exception as blend_error:
      print(f"depth hud blend: {blend_error}")

  def _consume_result(self) -> None:
    result = self._worker.take_result()
    if result is None:
      return
    self._last_depth = result.depth
    self._last_band = result.band
    self._near_obstacle = result.near_obstacle
    self._last_infer_ms = result.infer_ms

  def _maybe_submit(
    self, img, ball_snapshot: BallFollowSnapshot, now_ms: int,
  ) -> None:
    """Submit at most one fresh frame; skip entirely while the worker is busy.

    Skipping here must not stall ball follow: detect/track/drive live on the
    teleop path. Busy ⇒ keep last band; position tracking is independent.
    """
    if self._worker.busy():
      return
    if now_ms - self._last_submit_ms < self._settings.depth_interval_ms:
      return

    def _build():
      small = self._capture_infer_frame(img)
      if small is None:
        return None
      self._target_w = img.width()
      self._target_h = img.height()
      return (small, ball_snapshot.observation)

    if self._worker.try_submit(_build):
      self._last_submit_ms = now_ms

  def _capture_infer_frame(self, img):
    """Own a small RGB buffer the worker can read safely."""
    try:
      source = img.copy() if hasattr(img, "copy") else img
      small = self._infer_input(source)
      if small is source and hasattr(source, "copy"):
        return source.copy()
      if hasattr(small, "copy") and small is not source:
        # resize already allocated; keep it (worker consumes once).
        return small
      return small
    except MemoryError as oom:
      self._kill_after_oom(oom)
      return None
    except Exception as copy_error:
      print(f"depth: capture frame: {copy_error}")
      return None

  def _job(self, small, observation: BallObservation | None) -> DepthInferResult | None:
    """Worker entry: NN + band samples (+ optional upscale for paint)."""
    if maix_image is None or self._model is None:
      return None
    try:
      depth_small = self._model.get_depth_image(
        small, maix_image.Fit.FIT_CONTAIN, maix_image.CMap.TURBO,
      )
      if depth_small is None:
        return None
      near = self._estimate_near(depth_small, observation)
      band = self._classify_ball(depth_small, observation)
      depth = depth_small
      view = self._settings.depth_view
      if view is not DepthViewMode.RGB:
        tw = self._target_w
        th = self._target_h
        if tw > 0 and th > 0 and (
          depth_small.width() != tw or depth_small.height() != th
        ):
          if hasattr(depth_small, "resize"):
            depth = depth_small.resize(tw, th)
      return DepthInferResult(
        depth=depth, band=band, near_obstacle=near, infer_ms=0.0,
      )
    except MemoryError as oom:
      self._kill_after_oom(oom)
      return None

  def _maybe_log_timing(self, now_ms: int) -> None:
    if now_ms - self._last_timing_log_ms < _TIMING_LOG_MS:
      return
    self._last_timing_log_ms = now_ms
    print(
      f"depth: view={self._settings.depth_view.value} "
      f"infer={self._last_infer_ms:.0f}ms paint={self._last_paint_ms:.0f}ms "
      f"interval={self._settings.depth_interval_ms}ms "
      f"busy={int(self._worker.busy())}",
    )

  def _paint(self, img) -> None:
    """Apply HUD paint for the configured view mode (may be a no-op)."""
    view = self._settings.depth_view
    if view is DepthViewMode.RGB:
      return
    depth = self._last_depth
    if depth is None:
      return
    if view is DepthViewMode.DEPTH:
      self._replace_with_depth(img, depth)
      return
    self._blend_depth(img, depth)

  def _kill_after_oom(self, oom: BaseException) -> None:
    """Unload NN forever — packaged app must not exit on FB OOM."""
    print(f"depth: FB OOM — fusion disabled for this session: {oom}")
    self._oom_disabled = True
    self._error = "fb_oom"
    self._unload("oom")

  def _unload(self, reason: str) -> None:
    self._model = None
    self._last_depth = None
    self._last_band = BallDepthBand.UNKNOWN
    self._near_obstacle = False
    if reason == "oom":
      return

  def _ensure_full_size(self, img, depth):
    """Upscale depth to capture size when painting; keep result cached."""
    tw = img.width()
    th = img.height()
    if depth.width() == tw and depth.height() == th:
      return depth
    if not hasattr(depth, "resize"):
      return depth
    plane = depth.resize(tw, th)
    self._last_depth = plane
    return plane

  def _replace_with_depth(self, img, depth) -> None:
    """Opaque full-frame depth (no blend)."""
    plane = self._ensure_full_size(img, depth)
    img.draw_image(0, 0, plane)

  def _blend_depth(self, img, depth) -> None:
    """Alpha-blend upscaled depth onto the capture buffer (in place)."""
    plane = self._ensure_full_size(img, depth)
    rgb_a = max(0.0, min(1.0, float(self._settings.depth_rgb_alpha)))
    alpha_i = int(rgb_a * 256)
    if hasattr(img, "blend"):
      try:
        img.blend(plane, alpha=alpha_i)
        return
      except Exception as blend_error:
        print(f"depth: blend fallback to draw_image: {blend_error}")
    depth_a = max(0.0, min(1.0, 1.0 - rgb_a))
    try:
      if depth_a >= 0.99:
        img.draw_image(0, 0, plane)
      else:
        img.draw_image(0, 0, plane, alpha=depth_a)
    except TypeError:
      img.draw_image(0, 0, plane)

  def _draw_near_led(self, img) -> None:
    """Right-side orange LED when the forward ROI looks close."""
    cx = img.width() - 28
    cy = 28
    color = maix_image.Color.from_rgb(255, 120, 30)
    img.draw_circle(cx, cy, 12, color, thickness=-1)
    img.draw_circle(cx, cy, 12, maix_image.COLOR_WHITE, thickness=2)

  @staticmethod
  def _band_color(band: BallDepthBand):
    if band is BallDepthBand.CLOSE:
      return maix_image.Color.from_rgb(240, 60, 40)
    if band is BallDepthBand.OK:
      return maix_image.Color.from_rgb(80, 220, 80)
    if band is BallDepthBand.FAR:
      return maix_image.Color.from_rgb(60, 120, 240)
    return maix_image.Color.from_rgb(200, 200, 200)

  def _draw_ball_band(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    obs = ball_snapshot.observation
    band = self._last_band
    if obs is None or maix_image is None:
      return
    scale_x = img.width() / max(1, obs.image_width)
    scale_y = img.height() / max(1, obs.image_height)
    cx = int(obs.center_x * scale_x)
    cy = int(obs.center_y * scale_y)
    color = self._band_color(band)
    radius = max(8, int(max(obs.width, obs.height) * scale_x * 0.35))
    img.draw_circle(cx, cy, radius, color, thickness=3)

  def _try_load(self, model_path: str) -> None:
    if maix_nn is None:
      self._error = "no maix.nn"
      return
    try:
      self._model = maix_nn.DepthAnything(model_path, dual_buff=False)
      self._error = ""
      print(
        f"depth: loaded {model_path} "
        f"(dual_buff=False, async, infer≤{_INFER_MAX_W}x{_INFER_MAX_H}, "
        f"view={self._settings.depth_view.value})",
      )
    except MemoryError as oom:
      self._kill_after_oom(oom)
    except Exception as load_error:
      self._model = None
      self._error = str(load_error)
      print(f"depth: load failed: {load_error}")

  def _infer_input(self, img):
    """Downscale before NN — model is 322×238; full 640×480 blows the FB stack."""
    w = img.width()
    h = img.height()
    if w <= _INFER_MAX_W and h <= _INFER_MAX_H:
      return img
    if not hasattr(img, "resize"):
      return img
    scale = min(_INFER_MAX_W / max(1, w), _INFER_MAX_H / max(1, h))
    return img.resize(max(1, int(w * scale)), max(1, int(h * scale)))

  def _draw_contours_low_res(self, img) -> None:
    """Optional Canny + dilate on a half-res scratch, then blend."""
    # ponytail: half-res edges; upgrade = dedicated edge NN / GPU path.
    try:
      w = max(160, img.width() // 2)
      h = max(120, img.height() // 2)
      if not hasattr(img, "resize"):
        return
      small = img.resize(w, h)
      edge_type = maix_image.EdgeDetector.EDGE_CANNY
      small.find_edges(
        edge_type,
        threshold=[self._settings.depth_contour_low, self._settings.depth_contour_high],
      )
      thick = max(1, int(self._settings.depth_contour_thickness))
      if thick > 1 and hasattr(small, "dilate"):
        # dilate size is kernel radius-ish; thickness 2 → size 1, 3 → 2.
        small.dilate(max(1, thick - 1))
      edges = small.resize(img.width(), img.height()) if hasattr(small, "resize") else small
      alpha_i = int(max(0.0, min(1.0, self._settings.depth_contour_alpha)) * 256)
      try:
        img.blend(edges, alpha=256 - alpha_i)
      except Exception as contour_blend_error:
        print(f"depth: contour blend: {contour_blend_error}")
        img.draw_image(0, 0, edges)
    except MemoryError as oom:
      self._contours_disabled = True
      print(f"depth: contours disabled after OOM: {oom}")
    except Exception as edge_error:
      print(f"depth: contours: {edge_error}")

  def _classify_ball(
    self, depth_img, observation: BallObservation | None,
  ) -> BallDepthBand:
    """Map turbo warmth at the ball centre (+ size hint) to a distance band."""
    if observation is None:
      return BallDepthBand.UNKNOWN
    try:
      scale_x = depth_img.width() / max(1, observation.image_width)
      scale_y = depth_img.height() / max(1, observation.image_height)
      x = int(observation.center_x * scale_x)
      y = int(observation.center_y * scale_y)
      x = max(0, min(depth_img.width() - 1, x))
      y = max(0, min(depth_img.height() - 1, y))
      warmth = self._sample_warmth(depth_img, x, y)
      band = self._band_from_warmth(warmth)
      height = observation.height_ratio
      if height >= self._settings.too_close_height_ratio and band is not BallDepthBand.CLOSE:
        return BallDepthBand.CLOSE
      if height < self._settings.target_height_ratio * 0.55 and band is BallDepthBand.OK:
        return BallDepthBand.FAR
      return band
    except Exception as band_error:
      print(f"depth: ball band: {band_error}")
      return BallDepthBand.UNKNOWN

  def _band_from_warmth(self, warmth: float) -> BallDepthBand:
    if warmth >= self._settings.depth_close_warmth:
      return BallDepthBand.CLOSE
    if warmth <= self._settings.depth_far_warmth:
      return BallDepthBand.FAR
    return BallDepthBand.OK

  def _sample_warmth(self, depth_img, cx: int, cy: int) -> float:
    """Average (R−B)/255 in a small window — turbo warm = near."""
    total = 0.0
    count = 0
    for dy in (-2, 0, 2):
      for dx in (-2, 0, 2):
        x = max(0, min(depth_img.width() - 1, cx + dx))
        y = max(0, min(depth_img.height() - 1, cy + dy))
        pixel = depth_img.get_pixel(x, y)
        if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
          total += (int(pixel[0]) - int(pixel[2])) / 255.0
          count += 1
    return total / count if count else 0.0

  def _estimate_near(
    self, depth_img, observation: BallObservation | None,
  ) -> bool:
    """ROI ahead looks close (warm) while ball is absent/far in that band."""
    try:
      w = depth_img.width()
      h = depth_img.height()
      s = self._settings
      left = int(s.depth_roi_left_ratio * w)
      right = int(s.depth_roi_right_ratio * w)
      top = int(s.depth_roi_top_ratio * h)
      bottom = int(s.depth_roi_bottom_ratio * h)
      total = 0.0
      count = 0
      step_x = max(1, (right - left) // 8)
      step_y = max(1, (bottom - top) // 8)
      for y in range(top, bottom, step_y):
        for x in range(left, right, step_x):
          total += self._sample_warmth(depth_img, x, y)
          count += 1
      if count <= 0:
        return False
      mean_warmth = total / count
      ball_blocking = False
      if observation is not None and observation.height_ratio >= s.too_close_height_ratio * 0.7:
        ball_blocking = True
      return mean_warmth >= s.depth_close_warmth and not ball_blocking
    except Exception as near_error:
      print(f"depth: near estimate: {near_error}")
      return False
