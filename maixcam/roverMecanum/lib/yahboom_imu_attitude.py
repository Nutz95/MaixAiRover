"""Yahboom IMU attitude sample (degrees)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YahboomImuAttitude:
  """Board attitude from ``FUNC_REPORT_IMU_ATT``."""

  roll_deg: float
  pitch_deg: float
  yaw_deg: float
