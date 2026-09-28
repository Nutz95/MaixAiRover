"""Stand-in serial so Rosmaster.__del__ can call close() safely."""

from __future__ import annotations

import threading


class DummySerial:
  """No-op serial left on a dead Rosmaster handle after disconnect."""

  def close(self) -> None:
    """No-op."""
    return

  def read(self, size: int = 1):
    """Park forever if a stray RX thread still calls read."""
    del size
    threading.Event().wait()
    return b"\x00"

  def write(self, data):
    """Discard writes."""
    del data
    return 0

  @property
  def is_open(self) -> bool:
    """Always closed."""
    return False

  def isOpen(self) -> bool:
    """Legacy pyserial alias for ``is_open``."""
    return False
