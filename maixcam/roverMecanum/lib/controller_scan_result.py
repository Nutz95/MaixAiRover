"""Result of scanning for an Xbox controller MAC address."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerScanResult:
  """MAC discovery outcome used by the Bluetooth pairing flow."""

  mac: str = ""
  error: str = ""

  def ok(self) -> bool:
    """Return True when a MAC was found."""
    return bool(self.mac) and not self.error
