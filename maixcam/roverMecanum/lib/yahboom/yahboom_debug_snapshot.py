"""Immutable snapshot of Yahboom debug-panel UI state."""

from __future__ import annotations

from dataclasses import dataclass

from lib.motion.encoder_counts import EncoderCounts
from lib.yahboom.yahboom_battery import YahboomBattery
from lib.yahboom.yahboom_imu_attitude import YahboomImuAttitude


@dataclass(frozen=True)
class YahboomDebugSnapshot:
  """Panel open flag + live board sensors for DBG draw."""

  panel_open: bool
  status: str
  battery: YahboomBattery | None
  imu: YahboomImuAttitude | None
  encoders: EncoderCounts
