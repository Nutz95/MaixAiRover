"""Color-ball detector using the MaixPy image.find_blobs API."""

from typing import Iterable, List, Optional

from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_observation import BallObservation


class BallDetector:
  """Select the largest compact color blob without commanding motors."""

  def __init__(self, settings: BallFollowSettings):
    """Create a detector from already-validated ball-follow settings."""
    self._settings = settings

  def detect(
    self,
    frame,
    timestamp_ms: int,
    thresholds: Optional[List[List[int]]] = None,
  ) -> Optional[BallObservation]:
    """Detect and select one ball from an RGB888 MaixPy image."""
    if frame is None:
      return None
    image_width = frame.width()
    image_height = frame.height()
    active_thresholds = thresholds or self._settings.thresholds_for(
      self._settings.default_color,
    )
    blobs = frame.find_blobs(
      active_thresholds,
      area_threshold=self._settings.area_threshold,
      pixels_threshold=self._settings.pixels_threshold,
      merge=True,
    )
    candidates = []
    for blob in blobs:
      candidate = self._observation_from_blob(
        blob, image_width, image_height, timestamp_ms,
      )
      if candidate is not None:
        candidates.append(candidate)
    return self.select_best(candidates)

  @staticmethod
  def select_best(
    candidates: Iterable[BallObservation],
  ) -> Optional[BallObservation]:
    """Return the highest-scoring candidate, or None when no candidate exists."""
    best = None
    for candidate in candidates:
      if best is None or candidate.score > best.score:
        best = candidate
    return best

  def _observation_from_blob(
    self,
    blob,
    image_width: int,
    image_height: int,
    timestamp_ms: int,
  ) -> Optional[BallObservation]:
    """Convert one MaixPy blob to a filtered typed observation."""
    width = int(blob.w())
    height = int(blob.h())
    if width < self._settings.min_blob_width or height < self._settings.min_blob_height:
      return None
    aspect_ratio = width / max(1, height)
    if not (
      self._settings.min_aspect_ratio
      <= aspect_ratio
      <= self._settings.max_aspect_ratio
    ):
      return None
    compactness = max(0.0, 1.0 - abs(1.0 - aspect_ratio))
    area = int(blob.area())
    return BallObservation(
      center_x=int(blob.cx()),
      center_y=int(blob.cy()),
      width=width,
      height=height,
      area=area,
      score=area * compactness,
      timestamp_ms=timestamp_ms,
      image_width=image_width,
      image_height=image_height,
    )
