"""Chassis body-frame velocity for closed-loop boards (m/s and rad/s scale)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChassisVelocity:
  """Body-frame command: forward ``vx``, strafe ``vy``, yaw rate ``vz``."""

  vx: float = 0.0
  vy: float = 0.0
  vz: float = 0.0

  def is_idle(self, epsilon: float = 1e-4) -> bool:
    """True when all components are near zero."""
    return (
      abs(self.vx) <= epsilon
      and abs(self.vy) <= epsilon
      and abs(self.vz) <= epsilon
    )
