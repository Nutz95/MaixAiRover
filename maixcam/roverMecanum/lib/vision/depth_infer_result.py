"""One finished DepthAnything pass (HUD / band sampling)."""

from __future__ import annotations

from dataclasses import dataclass

from lib.vision.ball_depth_band import BallDepthBand


@dataclass
class DepthInferResult:
  """Depth plane plus derived ball/near cues from one NN pass."""

  depth: object
  band: BallDepthBand
  near_obstacle: bool
  infer_ms: float
