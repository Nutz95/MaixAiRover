"""Front + optional rear Waveshare link endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from lib.esp_board_endpoints import EspBoardEndpoints


@dataclass(frozen=True)
class EspLinkConfig:
  """Front + optional rear Waveshare endpoints (legacy flat esp{} supported)."""

  front: EspBoardEndpoints
  rear: EspBoardEndpoints | None = None

  @classmethod
  def from_mapping(cls, esp: dict) -> "EspLinkConfig":
    """Parse ``esp.front``/``esp.rear`` or legacy ``uart_port``/``wifi_host``."""
    if "front" in esp and isinstance(esp.get("front"), dict):
      front = EspBoardEndpoints.from_mapping(esp["front"], default_uart="uart4")
      rear_raw = esp.get("rear")
      rear = None
      if isinstance(rear_raw, dict) and str(rear_raw.get("uart_port", "")).strip():
        rear = EspBoardEndpoints.from_mapping(rear_raw, default_uart="uart2")
      return cls(front=front, rear=rear)
    return cls(
      front=EspBoardEndpoints(
        uart_port=str(esp.get("uart_port", "uart4")).strip() or "uart4",
        wifi_host=str(esp.get("wifi_host", "") or "").strip(),
        wifi_port=int(esp.get("wifi_port", 2333)),
      ),
      rear=None,
    )
