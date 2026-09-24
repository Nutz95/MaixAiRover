"""Typed green-ball observation produced by the vision detector."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BallObservation:
  """One plausible green blob expressed in image-relative measurements."""

  center_x: int
  center_y: int
  width: int
  height: int
  area: int
  score: float
  timestamp_ms: int
  image_width: int
  image_height: int

  @property
  def x_ratio(self) -> float:
    """Return the horizontal center in the range 0..1."""
    return self.center_x / max(1, self.image_width)

  @property
  def y_ratio(self) -> float:
    """Return the vertical center in the range 0..1."""
    return self.center_y / max(1, self.image_height)

  @property
  def height_ratio(self) -> float:
    """Return the blob height as a fraction of image height."""
    return self.height / max(1, self.image_height)

  @property
  def aspect_ratio(self) -> float:
    """Return width divided by height."""
    return self.width / max(1, self.height)
