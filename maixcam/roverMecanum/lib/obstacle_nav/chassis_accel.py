"""Signed chassis accel helpers from a calibrated IMU frame."""

from __future__ import annotations

from lib.obstacle_nav.imu_chassis_frame import ImuChassisFrame


class ChassisAccel:
  """Longitudinal / lateral accel relative to rest (forward/right > 0)."""

  def __init__(self, frame: ImuChassisFrame) -> None:
    """Bind to one session frame."""
    self._frame = frame

  def forward(self, ax: float, ay: float, az: float) -> float:
    """Signed forward accel (creep forward > 0)."""
    return self._frame.forward_accel(ax, ay, az)

  def lateral(self, ax: float, ay: float, az: float) -> float:
    """Signed rightward accel relative to rest (strafe right > 0)."""
    axis = self._frame.forward_accel_axis
    # Horizontal axis perpendicular to forward; default right = +Y if forward is X.
    if axis == 0:
      raw, rest = ay, self._frame.ay0
    elif axis == 1:
      raw, rest = ax, self._frame.ax0
    else:
      raw, rest = ax, self._frame.ax0
    # Keep the same handedness as forward_sign so right stays consistent after skip.
    return (raw - rest) * self._frame.forward_accel_sign

  def horizontal_peak(self, ax: float, ay: float, az: float) -> float:
    """Max |Δa| on the two horizontal axes (axis-agnostic body motion cue)."""
    return max(
      abs(ax - self._frame.ax0),
      abs(ay - self._frame.ay0),
    )
