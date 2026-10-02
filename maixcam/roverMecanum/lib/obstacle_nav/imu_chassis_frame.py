"""Session IMU rest pose and axis sign map for collision hints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImuChassisFrame:
  """Nominal attitude/accel and learned sign conventions after calib."""

  pitch0_deg: float
  roll0_deg: float
  pitch_forward_sign: float
  yaw_spin_sign: float
  ax0: float
  ay0: float
  az0: float
  forward_accel_axis: int
  forward_accel_sign: float

  @staticmethod
  def default() -> ImuChassisFrame:
    """Return identity mapping when calib was skipped (assume +X forward)."""
    return ImuChassisFrame(
      pitch0_deg=0.0,
      roll0_deg=0.0,
      pitch_forward_sign=1.0,
      yaw_spin_sign=1.0,
      ax0=0.0,
      ay0=0.0,
      az0=9.8,
      forward_accel_axis=0,
      forward_accel_sign=1.0,
    )

  def rest_accel_on_forward_axis(self) -> float:
    """Return rest accel component on the calibrated forward axis."""
    if self.forward_accel_axis == 1:
      return self.ay0
    if self.forward_accel_axis == 2:
      return self.az0
    return self.ax0

  def forward_accel(self, ax: float, ay: float, az: float) -> float:
    """Signed longitudinal accel relative to rest (forward creep > 0)."""
    if self.forward_accel_axis == 1:
      raw = ay
      rest = self.ay0
    elif self.forward_accel_axis == 2:
      raw = az
      rest = self.az0
    else:
      raw = ax
      rest = self.ax0
    return (raw - rest) * self.forward_accel_sign
