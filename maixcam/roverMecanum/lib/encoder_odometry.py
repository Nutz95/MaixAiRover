"""Odometry helpers based on encoder pulses and wheel geometry."""

import math

from lib.encoder_counts import EncoderCounts
from lib.motor_config import MotorConfig


class EncoderOdometry:
  """Convert encoder deltas into approximate chassis yaw."""

  def __init__(self, motor_config: MotorConfig) -> None:
    self._config = motor_config

  def pulses_per_wheel_revolution(self) -> float:
    """Return encoder pulses for one full wheel revolution."""
    return float(self._config.pulses_per_motor_rev) * float(self._config.gear_ratio)

  def meters_per_pulse(self) -> float:
    """Return linear metres travelled per encoder pulse at the wheel."""
    circumference = math.pi * (self._config.wheel_diameter_mm / 1000.0)
    return circumference / self.pulses_per_wheel_revolution()

  def yaw_degrees_from_delta(self, delta: EncoderCounts) -> float:
    """Estimate yaw change from a differential encoder delta (spin in place)."""
    left = (delta.m1 + delta.m3) / 2.0
    right = (delta.m2 + delta.m4) / 2.0
    # Opposite wheel signs when spinning: average magnitude.
    pulse_diff = (right - left) / 2.0
    arc_m = pulse_diff * self.meters_per_pulse()
    track_m = self._config.track_width_mm / 1000.0
    if track_m <= 0:
      return 0.0
    radians = arc_m / (track_m / 2.0)
    return math.degrees(radians)

  def pulses_for_yaw_degrees(self, angle_deg: float) -> int:
    """Estimate |pulses| each side should accumulate for an in-place yaw."""
    track_m = self._config.track_width_mm / 1000.0
    arc_m = abs(math.radians(angle_deg)) * (track_m / 2.0)
    pulses = arc_m / self.meters_per_pulse()
    return max(1, int(round(pulses)))
