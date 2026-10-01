"""Yahboom transport double: open OK, then fail a write (cable yank)."""

from __future__ import annotations


class FakeYahboomDropOnWriteTransport:
  """Simulates USB detach on the next bulk OUT after a good session."""

  def __init__(self) -> None:
    """Start closed; set ``fail_next_write`` to drop the link."""
    self.opened = False
    self.fail_next_write = False

  def open(self) -> None:
    """Mark the port open."""
    self.opened = True

  def close(self) -> None:
    """Mark the port closed."""
    self.opened = False

  def write(self, data: bytes) -> None:
    """Write or raise a CH340 bulk OUT failure when armed."""
    del data
    if not self.opened:
      raise OSError("transport not open")
    if self.fail_next_write:
      self.opened = False
      raise RuntimeError("CH340 bulk OUT failed rc=-4")

  def read(self, max_len: int = 256) -> bytes:
    """Empty RX while open; hard fail when closed."""
    del max_len
    if not self.opened:
      raise RuntimeError("CH340 bulk IN failed rc=-4")
    return b""
