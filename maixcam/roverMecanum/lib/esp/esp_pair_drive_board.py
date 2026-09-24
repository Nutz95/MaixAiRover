"""One Waveshare board: local motor pair via EspLinkPump (non-blocking)."""

from __future__ import annotations

from typing import Callable

from lib.motion.encoder_pair import EncoderPair


class EspPairDriveBoard:
  """Send a left/right wheel pair through a shared ESP link pump."""

  STOP_BURSTS = 4

  def __init__(
    self,
    set_drive: Callable[[int, int], None],
    max_setpoint: int = 50,
  ) -> None:
    self._set_drive = set_drive
    self._limit = max(1, max_setpoint)
    self._last_left: int | None = None
    self._last_right: int | None = None
    self._stop_bursts = 0

  def initialize(self, settle_s: float = 0.0) -> None:
    """No local init — ESP INIT is available from the DBG panel."""
    del settle_s
    self._last_left = None
    self._last_right = None
    self._stop_bursts = 0

  def set_pair(self, left: int, right: int) -> None:
    """Queue pair setpoints. On release, burst a few STOPs (UART can drop one)."""
    fl = self._clamp(left)
    fr = self._clamp(right)
    if fl == 0 and fr == 0:
      if self._last_left != 0 or self._last_right != 0:
        self._stop_bursts = self.STOP_BURSTS
        self._set_drive(0, 0)
        self._last_left = 0
        self._last_right = 0
      elif self._stop_bursts > 0:
        self._set_drive(0, 0)
        self._stop_bursts -= 1
      return
    self._stop_bursts = 0
    if self._last_left == fl and self._last_right == fr:
      return
    self._set_drive(fl, fr)
    self._last_left = fl
    self._last_right = fr

  def stop(self) -> None:
    """STOP both motors on this board."""
    self._last_left = None
    self._last_right = None
    self._stop_bursts = self.STOP_BURSTS
    self.set_pair(0, 0)

  def read_pair_encoders(self) -> EncoderPair:
    """Encoder totals come from TELEM, not this path."""
    return EncoderPair()

  def clear_encoders(self) -> None:
    """No-op until INIT is issued on the ESP."""
    return

  def _clamp(self, value: int) -> int:
    return max(-self._limit, min(self._limit, value))
