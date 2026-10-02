"""Why a stuck report was raised (drives HUD + optional cut-drive)."""

from __future__ import annotations

from enum import Enum


class StuckCause(Enum):
  """Classifier tag for StuckReport."""

  NONE = "none"
  ATTITUDE_TIP = "attitude_tip"
  CRASH = "crash"
  SOFT_IMPACT = "soft_impact"
  SLIP = "slip"
  YAW = "yaw"
  OTHER = "other"
