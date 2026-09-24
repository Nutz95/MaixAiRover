"""DepthAnything V2 fusion overlay — visual near-obstacle cue only."""

from __future__ import annotations

from time import monotonic

from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_follow_snapshot import BallFollowSnapshot

try:
  from maix import image as maix_image
  from maix import nn as maix_nn
except Exception as _maix_import_error:
  print(f"depth: maix unavailable: {_maix_import_error}")
  maix_image = None
  maix_nn = None


class DepthFusionHud:
  """Turbo depth base + RGB blend + optional near-obstacle badge (no drive)."""

  def __init__(self, settings: BallFollowSettings) -> None:
    """Load DepthAnything when enabled; degrade silently if the model is absent."""
    self._settings = settings
    self._model = None
    self._last_run_ms = 0
    self._last_depth = None
    self._near_obstacle = False
    self._error = ""
    if settings.depth_fusion_enabled:
      self._try_load(settings.depth_model_path)

  def apply_settings(self, settings: BallFollowSettings) -> None:
    """Hot-reload fusion flags; reload the NN only when the path changes."""
    old_path = self._settings.depth_model_path
    was_on = self._settings.depth_fusion_enabled
    self._settings = settings
    if not settings.depth_fusion_enabled:
      self._model = None
      self._last_depth = None
      self._near_obstacle = False
      return
    if self._model is None or settings.depth_model_path != old_path or not was_on:
      self._try_load(settings.depth_model_path)

  def draw(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    """Optionally replace the frame look with a depth+RGB fusion overlay."""
    if not self._settings.depth_fusion_enabled or maix_image is None:
      return
    if self._model is None:
      if self._error:
        img.draw_string(
          8, 110, f"DEPTH {self._error[:28]}", maix_image.COLOR_WHITE, scale=1.0,
        )
      return
    now_ms = int(monotonic() * 1000)
    if now_ms - self._last_run_ms >= self._settings.depth_interval_ms:
      self._last_run_ms = now_ms
      self._run_depth(img, ball_snapshot)
    depth = self._last_depth
    if depth is None:
      return
    try:
      try:
        img.draw_image(0, 0, depth, alpha=0.55)
      except TypeError:
        img.draw_image(0, 0, depth)
      if self._near_obstacle:
        badge = "NEAR OBS"
        size = maix_image.string_size(badge, scale=1.3, thickness=2)
        bx = img.width() - size.width() - 16
        by = 8
        img.draw_rect(
          bx - 4, by - 2, size.width() + 12, size.height() + 10,
          maix_image.Color.from_rgb(180, 40, 40), thickness=-1,
        )
        img.draw_string(
          bx, by + 2, badge, maix_image.COLOR_WHITE, scale=1.3, thickness=2,
        )
    except Exception as blend_error:
      print(f"depth hud blend: {blend_error}")

  def _try_load(self, model_path: str) -> None:
    if maix_nn is None:
      self._error = "no maix.nn"
      return
    try:
      self._model = maix_nn.DepthAnything(model_path, dual_buff=True)
      self._error = ""
      print(f"depth: loaded {model_path}")
    except Exception as load_error:
      self._model = None
      self._error = str(load_error)
      print(f"depth: load failed: {load_error}")

  def _run_depth(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    if maix_image is None or self._model is None:
      return
    try:
      depth = self._model.get_depth_image(
        img, maix_image.Fit.FIT_CONTAIN, maix_image.CMap.TURBO,
      )
      if depth is None:
        return
      self._last_depth = depth
      self._near_obstacle = self._estimate_near(depth, ball_snapshot)
    except Exception as infer_error:
      print(f"depth: infer failed: {infer_error}")

  def _estimate_near(self, depth_img, ball_snapshot: BallFollowSnapshot) -> bool:
    """Heuristic: ROI mean luminance high (close in turbo) while ball absent/far."""
    # ponytail: relative depth only; upgrade = metric calib + obstacle maneuver.
    try:
      w = depth_img.width()
      h = depth_img.height()
      s = self._settings
      left = int(s.depth_roi_left_ratio * w)
      right = int(s.depth_roi_right_ratio * w)
      top = int(s.depth_roi_top_ratio * h)
      bottom = int(s.depth_roi_bottom_ratio * h)
      roi_w = max(1, right - left)
      roi_h = max(1, bottom - top)
      total = 0
      count = 0
      step_x = max(1, roi_w // 8)
      step_y = max(1, roi_h // 8)
      for y in range(top, bottom, step_y):
        for x in range(left, right, step_x):
          pixel = depth_img.get_pixel(x, y)
          if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
            total += int(pixel[0]) + int(pixel[1]) + int(pixel[2])
            count += 1
          elif isinstance(pixel, int):
            total += pixel
            count += 1
      if count <= 0:
        return False
      mean = (total / count) / (3.0 * 255.0)
      ball_far_or_absent = True
      obs = ball_snapshot.observation
      if obs is not None and obs.height_ratio >= s.too_close_height_ratio * 0.7:
        ball_far_or_absent = False
      return mean >= s.depth_near_ratio and ball_far_or_absent
    except Exception as near_error:
      print(f"depth: near estimate: {near_error}")
      return False
