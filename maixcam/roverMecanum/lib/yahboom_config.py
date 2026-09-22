"""Typed Yahboom USB + closed-loop velocity limits."""

from __future__ import annotations

from dataclasses import dataclass

# Yahboom Rosmaster mecanum profile (X3).
YAHBOOM_CAR_TYPE_X3 = 0x01


@dataclass(frozen=True)
class YahboomConfig:
  """USB Rosmaster link + closed-loop velocity limits (X3 ranges)."""

  port: str
  baud: int = 115200
  car_type: int = YAHBOOM_CAR_TYPE_X3
  max_vx: float = 1.0
  max_vy: float = 1.0
  max_vz: float = 5.0

  @classmethod
  def from_mapping(cls, data: dict) -> "YahboomConfig":
    """Parse the ``yahboom`` block from config.json."""
    return cls(
      port=str(data.get("port", "") or "").strip(),
      baud=int(data.get("baud", 115200)),
      car_type=int(data.get("car_type", YAHBOOM_CAR_TYPE_X3)),
      max_vx=float(data.get("max_vx", 1.0)),
      max_vy=float(data.get("max_vy", 1.0)),
      max_vz=float(data.get("max_vz", 5.0)),
    )
