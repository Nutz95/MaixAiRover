"""ESP debug panel session — thin facade over EspLinkPump."""

from __future__ import annotations

from lib.esp_binary_client import EspBinaryClient
from lib.esp_link_pump import EspLinkPump
from lib.telem_snapshot import TelemSnapshot


class EspDebugSession:
  """Owns the shared UART pump used by teleop, HUD TELEM, and DBG."""

  def __init__(self, uart_port: str = "uart4") -> None:
    self._pump = EspLinkPump(uart_port=uart_port)

  def snapshot(self) -> tuple[bool, str, str, TelemSnapshot | None]:
    """Return ``(panel_open, link, status, telem)``."""
    return self._pump.snapshot()

  def telem(self) -> TelemSnapshot | None:
    """Latest TELEM snapshot (may be None)."""
    return self._pump.telem()

  def binary_client(self) -> EspBinaryClient | None:
    """Raw client (prefer ``set_drive`` for teleop)."""
    return self._pump.binary_client()

  def set_drive(self, fl: int, fr: int) -> None:
    """Queue FL/FR setpoints on the pump (non-blocking)."""
    self._pump.set_drive(fl, fr)

  def is_open(self) -> bool:
    """True while the debug panel should be shown."""
    return self._pump.is_panel_open()

  def start_link(self) -> None:
    """Ensure the UART pump is running (HUD + teleop)."""
    self._pump.start()

  def stop_link(self) -> None:
    """Stop the pump and close UART."""
    self._pump.stop()

  def open(self) -> None:
    """Show the debug panel."""
    self._pump.set_panel_open(True)

  def close(self) -> None:
    """Hide the debug panel; keep teleop link if still wanted."""
    self._pump.set_panel_open(False)

  def shutdown(self) -> None:
    """App exit."""
    self._pump.shutdown()

  def run_action(self, action: str) -> None:
    """Queue a DBG button action on the pump thread."""
    self._pump.queue_dbg(action)
