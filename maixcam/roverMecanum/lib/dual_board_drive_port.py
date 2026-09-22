"""Split mecanum setpoints across front + rear drive boards."""

from __future__ import annotations

from lib.encoder_counts import EncoderCounts
from lib.wheel_speeds import WheelSpeeds


class DualBoardDrivePort:
  """FL/FR → front board; RL/RR → rear board (noop OK until rear exists)."""

  def __init__(self, front, rear) -> None:
    self._front = front
    self._rear = rear

  def initialize(self, settle_s: float = 0.0) -> None:
    """Initialize front then rear."""
    self._front.initialize(settle_s=settle_s)
    self._rear.initialize(settle_s=0.0)

  def set_wheel_speeds(self, speeds: WheelSpeeds) -> None:
    """Dispatch front and rear pairs."""
    self._front.set_pair(int(speeds.front_left), int(speeds.front_right))
    self._rear.set_pair(int(speeds.rear_left), int(speeds.rear_right))

  def stop(self) -> None:
    """Stop both boards."""
    self._front.stop()
    self._rear.stop()

  def read_encoders(self) -> EncoderCounts:
    """Merge front (m1/m2) and rear (m3/m4) encoder totals."""
    front_pair = self._front.read_pair_encoders()
    rear_pair = self._rear.read_pair_encoders()
    return EncoderCounts(
      m1=front_pair.left,
      m2=front_pair.right,
      m3=rear_pair.left,
      m4=rear_pair.right,
    )

  def clear_encoders(self) -> None:
    """Clear encoders on both boards."""
    self._front.clear_encoders()
    self._rear.clear_encoders()
