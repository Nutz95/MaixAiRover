"""Immutable HUD snapshot for the IMU calib wizard."""

from __future__ import annotations

from dataclasses import dataclass

from lib.obstacle_nav.imu_calib_step import ImuCalibStep


@dataclass(frozen=True)
class ImuCalibSnapshot:
  """What the calib panel paints each frame."""

  step: ImuCalibStep
  title: str
  detail: str
  pitch_deg: float
  roll_deg: float
  yaw_deg: float
  can_confirm: bool
  can_skip: bool
  progress_ratio: float
