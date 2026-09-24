"""pyserial transport for Yahboom Rosmaster (CH340 @ 115200)."""

from __future__ import annotations


class YahboomSerialTransport:
  """Open a named serial port (COM* or /dev/*) for Rosmaster frames."""

  def __init__(self, port: str, baud: int = 115200) -> None:
    self._port_name = (port or "").strip()
    self._baud = int(baud)
    self._ser = None

  def open(self) -> None:
    """Open the serial port."""
    if not self._port_name:
      raise OSError("yahboom: empty serial port")
    try:
      import serial
    except ImportError as exc:
      raise OSError("yahboom: pyserial not installed") from exc
    self._ser = serial.Serial(self._port_name, self._baud, timeout=0.02)
    self._ser.reset_input_buffer()

  def close(self) -> None:
    """Close the serial port."""
    if self._ser is not None:
      try:
        self._ser.close()
      except Exception:
        pass
      self._ser = None

  def write(self, data: bytes) -> None:
    """Write raw bytes."""
    if self._ser is None:
      raise OSError("yahboom serial not open")
    self._ser.write(data)

  def read(self, max_len: int = 256) -> bytes:
    """Read up to ``max_len`` pending bytes."""
    if self._ser is None:
      return b""
    waiting = int(self._ser.in_waiting or 0)
    if waiting <= 0:
      return b""
    return self._ser.read(min(max_len, waiting))
