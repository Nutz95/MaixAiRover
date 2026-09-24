"""Line-protocol client for the Waveshare ESP coordinator over Maix UART."""

import time

# Disable system CommProtocol BEFORE opening any UART (stops UART4 spam/grab).
try:
  from maix import comm

  comm.CommProtocol.set_method("none")
except Exception as import_error:
  print(f"esp_uart: optional import: {import_error}")

from maix import err, pinmap, uart


class EspUartClient:
  """Open a MaixCAM2 UART and exchange ``OK``/``ERR`` lines with the ESP."""

  def __init__(
    self,
    device: str = "/dev/ttyS4",
    baud: int = 115200,
    tx_pin: str = "A21",
    tx_function: str = "UART4_TX",
    rx_pin: str = "A22",
    rx_function: str = "UART4_RX",
  ) -> None:
    self._device = device
    self._baud = baud
    self._tx_pin = tx_pin
    self._tx_function = tx_function
    self._rx_pin = rx_pin
    self._rx_function = rx_function
    self._ser = None

  @classmethod
  def from_port(cls, port: str = "uart4") -> "EspUartClient":
    """Build a client for ``uart4`` (A21/A22) or ``uart2`` (B0/B1 front header)."""
    key = (port or "uart4").strip().lower()
    if key in ("uart2", "ttys2", "b0"):
      return cls(
        device="/dev/ttyS2",
        baud=115200,
        tx_pin="B0",
        tx_function="UART2_TX",
        rx_pin="B1",
        rx_function="UART2_RX",
      )
    return cls()

  def open(self) -> None:
    """Map pins and open the UART device."""
    for pin, func in ((self._tx_pin, self._tx_function), (self._rx_pin, self._rx_function)):
      err.check_raise(pinmap.set_pin_function(pin, func), f"pinmap {pin}->{func}")
    print(f"EspUartClient open {self._device} {self._tx_pin}/{self._rx_pin}")
    self._ser = uart.UART(self._device, self._baud)
    time.sleep(0.15)
    for _ in range(8):
      chunk = self._ser.read()
      if not chunk:
        break
      time.sleep(0.02)

  def close(self) -> None:
    """Release the UART handle when possible."""
    self._ser = None

  def write_bytes(self, data: bytes) -> None:
    """Write raw bytes on the open UART."""
    if self._ser is None:
      raise RuntimeError("UART not open")
    self._ser.write(data)

  def read_bytes(self, max_len: int = 256) -> bytes:
    """Read available UART bytes (may be empty)."""
    if self._ser is None:
      raise RuntimeError("UART not open")
    chunk = self._ser.read()
    if not chunk:
      return b""
    return bytes(chunk[:max_len]) if len(chunk) > max_len else bytes(chunk)

  def command(self, line: str, timeout_s: float = 1.5) -> str:
    """Send one command line and return the first ``OK``/``ERR`` reply."""
    if self._ser is None:
      raise RuntimeError("UART not open")
    self._ser.write_str(line + "\n")
    deadline = time.time() + timeout_s
    buf = b""
    while time.time() < deadline:
      chunk = self._ser.read()
      if chunk:
        buf += chunk
        while b"\n" in buf:
          raw, buf = buf.split(b"\n", 1)
          text = raw.decode("utf-8", errors="replace").strip()
          if text.startswith("OK ") or text.startswith("ERR "):
            return text
      else:
        time.sleep(0.02)
    raise TimeoutError(f"no OK/ERR for {line!r} on {self._device} raw={buf!r}")
