"""Per-wheel motor setpoints for the Hiwonder driver."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WheelSpeeds:
  """Signed setpoints for FL, FR, RL, RR (mapped to M1..M4 by config)."""

  front_left: int = 0
  front_right: int = 0
  rear_left: int = 0
  rear_right: int = 0
