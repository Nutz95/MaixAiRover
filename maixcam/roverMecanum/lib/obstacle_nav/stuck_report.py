"""Latest stuck / collision analysis snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from lib.obstacle_nav.collision_side import CollisionSide
from lib.obstacle_nav.stuck_cause import StuckCause
from lib.obstacle_nav.stuck_level import StuckLevel


@dataclass(frozen=True)
class StuckReport:
  """Immutable stuck state for HUD and advisors."""

  level: StuckLevel
  side: CollisionSide
  detail: str
  cause: StuckCause = StuckCause.NONE

  @staticmethod
  def clear() -> StuckReport:
    """Return a nominal no-stuck report."""
    return StuckReport(
      level=StuckLevel.OK,
      side=CollisionSide.NONE,
      detail="",
      cause=StuckCause.NONE,
    )

  def cuts_drive(self) -> bool:
    """True when motors must stop (attitude tip only for now)."""
    return (
      self.level != StuckLevel.OK
      and self.cause == StuckCause.ATTITUDE_TIP
    )
