"""Proxy so Rosmaster's RX thread never indexes an empty ``read()``."""

from __future__ import annotations

import threading
import time


class GuardedSerial:
  """Wrap a live pyserial port; park reads after close instead of returning ``b''``.

  Rosmaster_Lib does ``bytearray(ser.read())[0]`` with no empty check. Closing the
  port would crash the daemon RX thread; after ``close()`` this proxy blocks forever.
  """

  def __init__(self, real) -> None:
    """Take ownership of an open serial-like object."""
    self._real = real
    self._closed = False
    self._park = threading.Event()
    self._lock = threading.Lock()

  def read(self, size: int = 1):
    """Block until one or more bytes, or park forever once closed."""
    while True:
      with self._lock:
        if self._closed:
          real = None
        else:
          real = self._real
      if real is None:
        self._park.wait()
        return b"\x00"
      try:
        data = real.read(size)
      except Exception:
        self.close()
        continue
      if data:
        return data
      time.sleep(0.005)

  def write(self, data):
    """Write bytes to the live port, or 0 if closed."""
    with self._lock:
      if self._closed or self._real is None:
        return 0
      return self._real.write(data)

  def flushInput(self) -> None:
    """Flush the input buffer when the port is still open."""
    with self._lock:
      if self._closed or self._real is None:
        return
      flush = getattr(self._real, "flushInput", None) or getattr(
        self._real, "reset_input_buffer", None,
      )
      if flush is not None:
        flush()

  def flushOutput(self) -> None:
    """Flush the output buffer when the port is still open."""
    with self._lock:
      if self._closed or self._real is None:
        return
      flush = getattr(self._real, "flushOutput", None) or getattr(
        self._real, "reset_output_buffer", None,
      )
      if flush is not None:
        flush()

  def close(self) -> None:
    """Close the real port and park future ``read()`` calls."""
    with self._lock:
      if self._closed:
        return
      self._closed = True
      real = self._real
      self._real = None
    if real is not None:
      try:
        real.close()
      except Exception:
        pass

  @property
  def is_open(self) -> bool:
    """True while the underlying port is still open."""
    with self._lock:
      if self._closed or self._real is None:
        return False
      return bool(getattr(self._real, "is_open", True))

  def isOpen(self) -> bool:
    """Legacy pyserial alias for ``is_open``."""
    return self.is_open

  def inWaiting(self) -> int:
    """Bytes waiting in the RX buffer, or 0 if closed."""
    with self._lock:
      if self._closed or self._real is None:
        return 0
      waiting = getattr(self._real, "in_waiting", None)
      if waiting is not None:
        return int(waiting)
      fn = getattr(self._real, "inWaiting", None)
      return int(fn()) if fn is not None else 0
