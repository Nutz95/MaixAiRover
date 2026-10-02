"""Result of soft avoidance blending."""

from __future__ import annotations

from dataclasses import dataclass

from lib.input.drive_output import DriveOutput
from lib.obstacle_nav.avoidance_hint import AvoidanceHint


@dataclass(frozen=True)
class AvoidanceDecision:
  """Blended drive axes plus HUD hint."""

  drive: DriveOutput
  hint: AvoidanceHint
