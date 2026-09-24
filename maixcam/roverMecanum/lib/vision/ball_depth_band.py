"""Relative ball-distance band from depth turbo colour (display only)."""

from __future__ import annotations

from enum import Enum


class BallDepthBand(Enum):
  """Heuristic range band sampled at the ball centre on a turbo depth map."""

  CLOSE = "close"   # red/orange — stop / too near (~≤15 cm)
  OK = "ok"         # yellow/green — hold (~15–25 cm)
  FAR = "far"       # blue — approach (~>25 cm)
  UNKNOWN = "unknown"
