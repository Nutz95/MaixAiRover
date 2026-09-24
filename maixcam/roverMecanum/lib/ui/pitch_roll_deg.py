"""Pitch and roll in degrees."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PitchRollDeg:
  """Attitude from accelerometer (degrees)."""

  pitch_deg: float
  roll_deg: float
