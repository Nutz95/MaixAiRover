"""Typed motor geometry and control settings."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class MotorConfig:
  """Hiwonder motor type, control mode, and mecanum channel mapping."""

  motor_type: int = 3
  encoder_polarity: int = 0
  control_mode: str = "speed"
  max_setpoint: int = 50
  channel_order: List[str] = field(default_factory=lambda: ["FL", "FR", "RL", "RR"])
  invert: List[bool] = field(default_factory=lambda: [False, False, False, False])
  wheel_diameter_mm: float = 96.0
  track_width_mm: float = 200.0
  pulses_per_motor_rev: int = 44
  gear_ratio: float = 56.0

  @staticmethod
  def from_mapping(raw: dict) -> "MotorConfig":
    """Build a MotorConfig from a config.json ``motors`` object."""
    if not isinstance(raw, dict):
      raw = {}
    order = raw.get("channel_order", ["FL", "FR", "RL", "RR"])
    invert = raw.get("invert", [False, False, False, False])
    mode = str(raw.get("control_mode", "speed")).strip().lower()
    if mode not in ("speed", "pwm"):
      mode = "speed"
    return MotorConfig(
      motor_type=int(raw.get("type", 3)),
      encoder_polarity=int(raw.get("encoder_polarity", 0)),
      control_mode=mode,
      max_setpoint=int(raw.get("max_setpoint", 50)),
      channel_order=[str(x) for x in order],
      invert=[bool(x) for x in invert],
      wheel_diameter_mm=float(raw.get("wheel_diameter_mm", 96.0)),
      track_width_mm=float(raw.get("track_width_mm", 200.0)),
      pulses_per_motor_rev=int(raw.get("pulses_per_motor_rev", 44)),
      gear_ratio=float(raw.get("gear_ratio", 56.0)),
    )
