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
from lib.vision.depth_warmth_sampler import DepthWarmthSampler
from lib.obstacle_nav.nav_roi_layout import NavRoiLayout

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
    self._last_depth_paint = None
    self._last_band = BallDepthBand.UNKNOWN
    self._near_obstacle = False
    self._error = ""
    self._oom_disabled = False
    self._contours_disabled = False
    self._last_infer_ms = 0.0
    self._last_paint_ms = 0.0
    self._last_timing_log_ms = 0
    self._frame_width = 0
    self._frame_height = 0
    self._worker = DepthInferWorker(self._job)
    self._nav_roi: NavRoiLayout | None = None
    self._warmth = DepthWarmthSampler()
  def last_depth_image(self):
    """Return the last turbo depth plane (infer or full size), or None."""
    return self._last_depth
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
      self._last_depth_paint = None
  def draw(
    self,
    img,
    ball_snapshot: BallFollowSnapshot,
    nav_roi: NavRoiLayout | None = None,
    *,
    force_depth_paint: bool = False,
    enabled: bool = True,
  ) -> None:
    """Paint last depth result; submit a new async job when due.

    ``enabled=False`` skips infer/paint (fluid MANUAL mode). Ground calib can
    still force paint via ``force_depth_paint``.
    """
    self._nav_roi = nav_roi
    if not enabled and not force_depth_paint:
      return
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
      if enabled:
        self._maybe_submit(img, ball_snapshot, now_ms)
      paint_t0 = monotonic()
      if force_depth_paint and self._last_depth is not None:
        self._replace_with_depth(img, self._last_depth)
      elif enabled:
        self._paint(img)
      self._last_paint_ms = (monotonic() - paint_t0) * 1000.0
      if force_depth_paint:
        self._maybe_log_timing(now_ms)
        return
      if not enabled:
        return
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
    self._last_depth_paint = None
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
      self._frame_width = img.width()
      self._frame_height = img.height()
      return (small, ball_snapshot.observation)

    if self._worker.try_submit(_build):
      self._last_submit_ms = now_ms
  def _capture_infer_frame(self, img):
    """Own a small RGB buffer the worker can read safely.

    Resize first — never full-frame copy (that stalls the HUD).
    """
    try:
      small = self._infer_input(img)
      if small is img:
        return self._copy_image(img)
      return small
    except MemoryError as oom:
      self._kill_after_oom(oom)
      return None
    except Exception as copy_error:
      print(f"depth: capture frame: {copy_error}")
      return None
  @staticmethod
  def _copy_image(img):
    """Return ``img.copy()`` when MaixPy supports it, else the same buffer."""
    try:
      return img.copy()
    except AttributeError:
      return img
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
      near = self._warmth.estimate_near(
        depth_small,
        observation,
        self._settings,
        self._nav_roi,
        self._frame_width,
        self._frame_height,
      )
      band = self._warmth.classify_ball(depth_small, observation, self._settings)
      return DepthInferResult(
        depth=depth_small, band=band, near_obstacle=near, infer_ms=0.0,
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
    self._last_depth_paint = None
    self._last_band = BallDepthBand.UNKNOWN
    self._near_obstacle = False
    if reason == "oom":
      return
  def _ensure_full_size(self, img, depth):
    """Upscale depth for HUD paint only — keep ``_last_depth`` at infer size."""
    paint_width = img.width()
    paint_height = img.height()
    if (
      self._last_depth_paint is not None
      and self._last_depth_paint.width() == paint_width
      and self._last_depth_paint.height() == paint_height
    ):
      return self._last_depth_paint
    if depth.width() == paint_width and depth.height() == paint_height:
      self._last_depth_paint = depth
      return depth
    try:
      plane = depth.resize(paint_width, paint_height)
    except AttributeError:
      return depth
    self._last_depth_paint = plane
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
    try:
      img.blend(plane, alpha=alpha_i)
      return
    except AttributeError:
      print("depth: blend unsupported, draw_image fallback")
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
    width = img.width()
    height = img.height()
    if width <= _INFER_MAX_W and height <= _INFER_MAX_H:
      return img
    scale = min(_INFER_MAX_W / max(1, width), _INFER_MAX_H / max(1, height))
    try:
      return img.resize(max(1, int(width * scale)), max(1, int(height * scale)))
    except AttributeError:
      return img
  def _draw_contours_low_res(self, img) -> None:
    """Optional Canny + dilate on a half-res scratch, then blend."""
    # ponytail: half-res edges; upgrade = dedicated edge NN / GPU path.
    try:
      width = max(160, img.width() // 2)
      height = max(120, img.height() // 2)
      try:
        small = img.resize(width, height)
      except AttributeError:
        print("depth: contours skipped (no resize)")
        return
      edge_type = maix_image.EdgeDetector.EDGE_CANNY
      small.find_edges(
        edge_type,
        threshold=[self._settings.depth_contour_low, self._settings.depth_contour_high],
      )
      thick = max(1, int(self._settings.depth_contour_thickness))
      if thick > 1:
        try:
          # dilate size is kernel radius-ish; thickness 2 → size 1, 3 → 2.
          small.dilate(max(1, thick - 1))
        except AttributeError:
          print("depth: dilate unsupported, thin contours")
      try:
        edges = small.resize(img.width(), img.height())
      except AttributeError:
        edges = small
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
