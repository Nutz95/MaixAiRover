"""Yahboom raw accelerometer sample (m/s^2, board frame)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YahboomImuAccel:
  """Triaxial accel from ``FUNC_REPORT_MPU_RAW`` / ``ICM_RAW``."""

  ax: float
  ay: float
  az: float
