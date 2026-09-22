"""Minimal byte pipe for Yahboom (and tests)."""

from __future__ import annotations

from typing import Protocol


class ByteTransport(Protocol):
  """Open/close + raw read/write used by YahboomDriveBoard."""

  def open(self) -> None:
    """Open the underlying device."""

  def close(self) -> None:
    """Close the device."""

  def write(self, data: bytes) -> None:
    """Send bytes."""

  def read(self, max_len: int = 256) -> bytes:
    """Read available bytes (may be empty)."""
