"""USB CP210x line-protocol client (Maix USB host → Waveshare UART0)."""

import time

from lib.cp210x_usb_serial import Cp210xUsbSerial


class EspUsbClient:
  """Exchange ``OK``/``ERR`` lines over the CP210x userspace serial bridge."""

  def __init__(self, baud: int = 115200) -> None:
    self._port = Cp210xUsbSerial(baud)

  def open(self) -> None:
    """Open the CP210x device."""
    self._port.open()
    time.sleep(0.05)
    self._port.read(512, timeout_ms=50)

  def close(self) -> None:
    """Close the CP210x device."""
    self._port.close()

  def write_bytes(self, data: bytes) -> None:
    """Write raw bytes on the CP210x bridge."""
    self._port.write(data)

  def read_bytes(self, max_len: int = 256) -> bytes:
    """Read available CP210x bytes (may be empty)."""
    return self._port.read(max_len, timeout_ms=40)

  def command(self, line: str, timeout_s: float = 1.5) -> str:
    """Send one command line and return the first ``OK``/``ERR`` reply."""
    self._port.write_str(line + "\n")
    deadline = time.time() + timeout_s
    buf = b""
    while time.time() < deadline:
      chunk = self._port.read(256, timeout_ms=40)
      if chunk:
        buf += chunk
        while b"\n" in buf:
          raw, buf = buf.split(b"\n", 1)
          text = raw.decode("utf-8", errors="replace").strip()
          if text.startswith("OK ") or text.startswith("ERR "):
            return text
      else:
        time.sleep(0.02)
    raise TimeoutError(f"no OK/ERR for {line!r} raw={buf!r}")
