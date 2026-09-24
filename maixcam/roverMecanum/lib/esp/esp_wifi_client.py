"""TCP line-protocol client for the ESP WiFi console (port 2333)."""

import socket
import time


class EspWifiClient:
  """Exchange ``OK``/``ERR`` lines with the ESP coordinator TCP console."""

  def __init__(self, host: str, port: int = 2333) -> None:
    self._host = host
    self._port = port
    self._sock = None
    self._buf = b""

  def open(self) -> None:
    """Connect to the ESP TCP console."""
    self._sock = socket.create_connection((self._host, self._port), timeout=2.0)
    self._sock.settimeout(0.2)
    time.sleep(0.15)
    self._drain()

  def close(self) -> None:
    """Close the TCP socket."""
    if self._sock is not None:
      try:
        self._sock.close()
      except OSError as swallowed:
        print(f"esp_wifi_client.py: {swallowed}")
    self._sock = None

  def command(self, line: str, timeout_s: float = 2.0) -> str:
    """Send one command line and return the first ``OK``/``ERR`` reply."""
    if self._sock is None:
      raise RuntimeError("socket not open")
    self._sock.sendall((line + "\n").encode("ascii"))
    deadline = time.time() + timeout_s
    while time.time() < deadline:
      reply = self._read_reply()
      if reply is not None:
        return reply
      time.sleep(0.02)
    raise TimeoutError(f"no OK/ERR for {line!r}")

  def _drain(self) -> None:
    try:
      while True:
        chunk = self._sock.recv(4096)
        if not chunk:
          break
        self._buf += chunk
    except (OSError, socket.timeout) as swallowed:
      print(f"esp_wifi_client.py: {swallowed}")

  def _read_reply(self):
    try:
      chunk = self._sock.recv(4096)
      if chunk:
        self._buf += chunk
    except socket.timeout as swallowed:
      print(f"esp_wifi_client.py: {swallowed}")
    except OSError:
      return None
    while b"\n" in self._buf:
      raw, self._buf = self._buf.split(b"\n", 1)
      text = raw.decode("utf-8", errors="replace").strip()
      if text.startswith("OK ") or text.startswith("ERR "):
        return text
    return None
