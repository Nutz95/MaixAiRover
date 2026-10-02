"""Soft drive override from obstacle L/C/R warmth (strafe-first)."""

from __future__ import annotations

from lib.input.drive_output import DriveOutput
from lib.obstacle_nav.avoidance_decision import AvoidanceDecision
from lib.obstacle_nav.avoidance_hint import AvoidanceHint
from lib.obstacle_nav.obstacle_band_reading import ObstacleBandReading
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings


class AvoidancePolicy:
  """Blend user/ball drive with depth bands — no planner, strafe-first."""

  def decide(
    self,
    drive: DriveOutput,
    reading: ObstacleBandReading,
    settings: ObstacleNavSettings,
  ) -> AvoidanceDecision:
    """Return blended axes + HUD hint. No-op when avoidance disabled."""
    if not settings.avoidance_enabled:
      return AvoidanceDecision(drive=drive, hint=AvoidanceHint.NONE)
    close = settings.avoidance_close_warmth
    caution = settings.avoidance_caution_warmth
    left_hot = reading.left >= close
    center_hot = reading.center >= close
    right_hot = reading.right >= close
    left_warm = reading.left >= caution
    right_warm = reading.right >= caution

    out = DriveOutput(
      axis_strafe=drive.axis_strafe,
      axis_forward=drive.axis_forward,
      axis_spin=drive.axis_spin,
      axis_pivot=drive.axis_pivot,
      preset_action=drive.preset_action,
    )

    if center_hot and left_hot and right_hot:
      out.axis_forward = max(out.axis_forward, settings.avoidance_reverse_axis)
      out.axis_strafe = 0
      return AvoidanceDecision(drive=out, hint=AvoidanceHint.REVERSE)

    if center_hot or (left_hot and right_hot):
      if reading.left + 0.05 < reading.right:
        out.axis_strafe = -settings.avoidance_strafe_axis
        out.axis_forward = min(out.axis_forward, 0)
        return AvoidanceDecision(drive=out, hint=AvoidanceHint.STRAFE_LEFT)
      if reading.right + 0.05 < reading.left:
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

    if center_hot or reading.center >= caution:
      if out.axis_forward < 0:
        out.axis_forward = 0
      hint = AvoidanceHint.STOP_FORWARD
      if left_warm and not right_warm:
        out.axis_strafe = max(out.axis_strafe, settings.avoidance_strafe_axis // 2)
        hint = AvoidanceHint.STRAFE_RIGHT
      elif right_warm and not left_warm:
        out.axis_strafe = min(out.axis_strafe, -settings.avoidance_strafe_axis // 2)
        hint = AvoidanceHint.STRAFE_LEFT
      return AvoidanceDecision(drive=out, hint=hint)

    return AvoidanceDecision(drive=out, hint=AvoidanceHint.NONE)
