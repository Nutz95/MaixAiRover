"""One teleop instant for stuck detection windows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotionProbeSample:
  """IMU, accel, encoder totals, and last drive axes at one timestamp."""

  timestamp_ms: int
  pitch_deg: float
  roll_deg: float
  yaw_deg: float
  ax: float
  ay: float
  az: float
  encoder_sum: int
  axis_forward: int
  axis_spin: int
  axis_strafe: int = 0
  accel_valid: bool = True
