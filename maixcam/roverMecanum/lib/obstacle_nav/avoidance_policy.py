"""Soft drive override from multi-column obstacle warmth (strafe-first)."""

from __future__ import annotations

from lib.input.drive_output import DriveOutput
from lib.obstacle_nav.avoidance_decision import AvoidanceDecision
from lib.obstacle_nav.avoidance_hint import AvoidanceHint
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


class AvoidancePolicy:
  """Blend user/ball drive with depth columns — corridor-aware, strafe-first."""

  def decide(
    self,
    drive: DriveOutput,
    reading: ObstacleBandReading,
    settings: ObstacleNavSettings,
  ) -> AvoidanceDecision:
    """Return blended axes + HUD hint. No-op when avoidance disabled."""
    if not settings.avoidance_enabled or reading.column_count() < 1:
      return AvoidanceDecision(drive=drive, hint=AvoidanceHint.NONE)
    close = settings.avoidance_close_warmth
    caution = settings.avoidance_caution_warmth
    out = DriveOutput(
      axis_strafe=drive.axis_strafe,
      axis_forward=drive.axis_forward,
      axis_spin=drive.axis_spin,
      axis_pivot=drive.axis_pivot,
      preset_action=drive.preset_action,
    )
    columns = reading.columns
    mid = reading.column_count() // 2
    left_cols = columns[:mid]
    right_cols = columns[mid + 1 :]
    left_hot = any(warmth >= close for warmth in left_cols)
    right_hot = any(warmth >= close for warmth in right_cols)
    # Single middle column = the gap lane (neighbors are often wall bleed).
    center_hot = columns[mid] >= close
    center_mean = columns[mid]
    left_mean = reading.left_mean()
    right_mean = reading.right_mean()

    if all(warmth >= close for warmth in columns):
      out.axis_forward = max(out.axis_forward, settings.avoidance_reverse_axis)
      out.axis_strafe = 0
      return AvoidanceDecision(drive=out, hint=AvoidanceHint.REVERSE)

    # Corridor: walls L/R, gap in the middle → keep going, do not panic-reverse.
    if left_hot and right_hot and not center_hot:
      if center_mean >= caution and out.axis_forward < 0:
        out.axis_forward = 0
        return AvoidanceDecision(drive=out, hint=AvoidanceHint.STOP_FORWARD)
      return AvoidanceDecision(drive=out, hint=AvoidanceHint.NONE)

    if center_hot:
      if left_mean + 0.05 < right_mean:
        out.axis_strafe = -settings.avoidance_strafe_axis
        out.axis_forward = min(out.axis_forward, 0)
        return AvoidanceDecision(drive=out, hint=AvoidanceHint.STRAFE_LEFT)
      if right_mean + 0.05 < left_mean:
        out.axis_strafe = settings.avoidance_strafe_axis
        out.axis_forward = min(out.axis_forward, 0)
        return AvoidanceDecision(drive=out, hint=AvoidanceHint.STRAFE_RIGHT)
      out.axis_forward = max(out.axis_forward, settings.avoidance_reverse_axis)
      return AvoidanceDecision(drive=out, hint=AvoidanceHint.REVERSE)

    if left_hot and not right_hot:
      out.axis_strafe = max(out.axis_strafe, settings.avoidance_strafe_axis)
      out.axis_forward = min(out.axis_forward, 0)
      return AvoidanceDecision(drive=out, hint=AvoidanceHint.STRAFE_RIGHT)

    if right_hot and not left_hot:
      out.axis_strafe = min(out.axis_strafe, -settings.avoidance_strafe_axis)
      out.axis_forward = min(out.axis_forward, 0)
      return AvoidanceDecision(drive=out, hint=AvoidanceHint.STRAFE_LEFT)

    if center_mean >= caution:
      if out.axis_forward < 0:
        out.axis_forward = 0
      hint = AvoidanceHint.STOP_FORWARD
      if left_mean >= caution and right_mean < caution:
        out.axis_strafe = max(out.axis_strafe, settings.avoidance_strafe_axis // 2)
        hint = AvoidanceHint.STRAFE_RIGHT
      elif right_mean >= caution and left_mean < caution:
        out.axis_strafe = min(out.axis_strafe, -settings.avoidance_strafe_axis // 2)
        hint = AvoidanceHint.STRAFE_LEFT
      return AvoidanceDecision(drive=out, hint=hint)

    return AvoidanceDecision(drive=out, hint=AvoidanceHint.NONE)
