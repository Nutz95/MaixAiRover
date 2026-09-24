"""Binary Maix↔ESP link (UART4 preferred, USB CP210x fallback)."""

from __future__ import annotations

import struct
import threading
import time

from lib.esp.esp_binary_protocol import (
  CMD_PING,
  CMD_PWM,
  CMD_SPEED,
  CMD_STOP,
  CMD_TELEM,
  RSP_ACK,
  RSP_ERR,
  RSP_PONG,
  RSP_TELEM,
  encode_frame,
  try_parse_frame,
)
from lib.esp.esp_exchange_result import EspExchangeResult
from lib.esp.esp_uart_client import EspUartClient
from lib.esp.esp_usb_client import EspUsbClient
from lib.esp.telem_snapshot import TelemSnapshot


class EspBinaryClient:
  """Open a link and exchange binary frames with the ESP coordinator."""

  def __init__(self, uart_port: str = "uart4") -> None:
    self._uart_port = uart_port
    self._transport = None
    self._link_name = ""
    self._rx = b""
    self._io_lock = threading.Lock()

  @property
  def link_name(self) -> str:
    """Human label for the active transport (``UART`` / ``USB``)."""
    return self._link_name

  def open(self) -> None:
    """Try UART4 then USB; raise if neither answers a binary PING."""
    self.close()
    for name, factory in (
      ("UART", lambda: EspUartClient.from_port(self._uart_port)),
      ("USB", EspUsbClient),
    ):
      client = factory()
      try:
        client.open()
        self._transport = client
        self._link_name = name
        self._rx = b""
        self.ping(timeout_s=0.8)
        return
      except Exception:
        try:
          client.close()
        except Exception:
          pass
        self._transport = None
        self._link_name = ""
    raise RuntimeError("no ESP binary link (UART4 / USB)")

  def close(self) -> None:
    """Release the transport."""
    with self._io_lock:
      if self._transport is not None:
        try:
          self._transport.close()
        except Exception:
          pass
      self._transport = None
      self._link_name = ""
      self._rx = b""

  def write_frame(self, msg_type: int, payload: bytes = b"") -> None:
    """Write one frame; do not wait for a reply (teleop path)."""
    with self._io_lock:
      if self._transport is None:
        raise RuntimeError("not open")
      self._transport.write_bytes(encode_frame(msg_type, payload))

  def write_speed(self, fl: int, fr: int, rl: int = 0, rr: int = 0) -> None:
    """Fire-and-forget CMD_SPEED."""
    self.write_frame(CMD_SPEED, struct.pack("bbbb", fl, fr, rl, rr))

  def write_telem(self) -> None:
    """Fire CMD_TELEM request (pair with ``poll_telem``)."""
    self.write_frame(CMD_TELEM, b"")

  def drain(self, max_s: float = 0.005) -> None:
    """Discard RX bytes for up to ``max_s`` (ACK cleanup after fire-and-forget)."""
    with self._io_lock:
      self._drain_unlocked(max_s)

  def poll_telem(self, max_s: float = 0.01) -> TelemSnapshot | None:
    """Read RX briefly; return a TELEM snapshot if one frame arrives."""
    with self._io_lock:
      if self._transport is None:
        return None
      deadline = time.time() + max_s
      while time.time() < deadline:
        chunk = self._transport.read_bytes(256)
        if chunk:
          self._rx += chunk
          while True:
            parsed = try_parse_frame(self._rx)
            if parsed is None:
              break
            self._rx = parsed.rest
            if parsed.cmd == RSP_TELEM:
              return TelemSnapshot.from_payload(parsed.payload)
        else:
          time.sleep(0.001)
      return None

  def ping(self, timeout_s: float = 1.0) -> None:
    """Send CMD_PING and expect RSP_PONG."""
    result = self._exchange(CMD_PING, b"", expect=RSP_PONG, timeout_s=timeout_s)
    if result.cmd != RSP_PONG:
      raise RuntimeError(f"unexpected ping rsp 0x{result.cmd:02X}")

  def stop(self, timeout_s: float = 1.0) -> None:
    """Send CMD_STOP and expect ACK."""
    self._expect_ack(CMD_STOP, b"", timeout_s)

  def speed(self, fl: int, fr: int, rl: int = 0, rr: int = 0, timeout_s: float = 1.0) -> None:
    """Send CMD_SPEED (4×int8) and wait for ACK."""
    self._expect_ack(CMD_SPEED, struct.pack("bbbb", fl, fr, rl, rr), timeout_s)

  def pwm(self, fl: int, fr: int, rl: int = 0, rr: int = 0, timeout_s: float = 1.0) -> None:
    """Send CMD_PWM (4×int8) and wait for ACK."""
    self._expect_ack(CMD_PWM, struct.pack("bbbb", fl, fr, rl, rr), timeout_s)

  def telem(self, timeout_s: float = 1.0) -> TelemSnapshot:
    """Request a telemetry snapshot (blocking)."""
    result = self._exchange(CMD_TELEM, b"", expect=RSP_TELEM, timeout_s=timeout_s)
    if result.cmd != RSP_TELEM:
      raise RuntimeError(f"unexpected telem rsp 0x{result.cmd:02X}")
    return TelemSnapshot.from_payload(result.payload)

  def text_command(self, line: str, timeout_s: float = 1.5) -> str:
    """Send a text line on the same link (INIT/HELP/etc.)."""
    with self._io_lock:
      if self._transport is None:
        raise RuntimeError("not open")
      self._rx = b""
      return self._transport.command(line, timeout_s=timeout_s)

  def _expect_ack(self, cmd: int, payload: bytes, timeout_s: float) -> None:
    result = self._exchange(cmd, payload, expect=RSP_ACK, timeout_s=timeout_s)
    if result.cmd == RSP_ERR:
      code = result.payload[0] if result.payload else 0
      raise RuntimeError(f"ESP ERR code={code}")
    if result.cmd != RSP_ACK:
      raise RuntimeError(f"unexpected ack rsp 0x{result.cmd:02X}")

  def _drain_unlocked(self, max_s: float) -> None:
    if self._transport is None:
      return
    deadline = time.time() + max_s
    self._rx = b""
    while time.time() < deadline:
      chunk = self._transport.read_bytes(256)
      if not chunk:
        break

  def _exchange(
    self,
    msg_type: int,
    payload: bytes,
    *,
    expect: int,
    timeout_s: float,
  ) -> EspExchangeResult:
    with self._io_lock:
      if self._transport is None:
        raise RuntimeError("not open")
      self._drain_unlocked(0.002)
      self._transport.write_bytes(encode_frame(msg_type, payload))
      deadline = time.time() + timeout_s
      while time.time() < deadline:
        chunk = self._transport.read_bytes(256)
        if chunk:
          self._rx += chunk
          while True:
            parsed = try_parse_frame(self._rx)
            if parsed is None:
              break
            self._rx = parsed.rest
            if parsed.cmd == expect or parsed.cmd == RSP_ERR:
              return EspExchangeResult(cmd=parsed.cmd, payload=parsed.payload)
        else:
          time.sleep(0.001)
      self._rx = b""
      raise TimeoutError(f"no binary reply for 0x{msg_type:02X}")
