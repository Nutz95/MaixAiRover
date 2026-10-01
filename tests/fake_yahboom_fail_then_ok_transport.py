"""Yahboom transport double: first open fails, later opens succeed."""

from __future__ import annotations


class FakeYahboomFailThenOkTransport:
  """Simulates CH340 missing, then plugged in on a later try_open."""

  def __init__(self) -> None:
    """Start closed; first open() raises."""
    self.opens = 0
    self.opened = False
    self.writes = 0

  def open(self) -> None:
    """Fail once, then mark the port open."""
    self.opens += 1
    if self.opens < 2:
      raise RuntimeError("CH340 1a86:7523 not found (USB host + Yahboom Micro-USB?)")
    self.opened = True

  def close(self) -> None:
    """Mark the port closed."""
    self.opened = False

  def write(self, data: bytes) -> None:
    """Count writes; fail if not open."""
    del data
    if not self.opened:
      raise OSError("transport not open")
    self.writes += 1

  def read(self, max_len: int = 256) -> bytes:
    """Return empty RX (no auto-report in this double)."""
    del max_len
    return b""
