"""UART + optional WiFi endpoints for one Waveshare board."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EspBoardEndpoints:
  """UART port name and optional WiFi console for one drive board."""

  uart_port: str
  wifi_host: str = ""
  wifi_port: int = 2333

  @classmethod
  def from_mapping(cls, data: dict, *, default_uart: str = "uart4") -> "EspBoardEndpoints":
    """Parse one board block from config.json."""
    return cls(
      uart_port=str(data.get("uart_port", default_uart)).strip() or default_uart,
      wifi_host=str(data.get("wifi_host", "") or "").strip(),
      wifi_port=int(data.get("wifi_port", 2333)),
    )
