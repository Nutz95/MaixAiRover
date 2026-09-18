"""Bluetooth pairing/connect command result."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BluetoothCommandResult:
  """Outcome of a bluetoothctl pairing or connect operation."""

  output: str = ""
  error: str = ""

  def ok(self) -> bool:
    """Return True when the command reported no error string."""
    return not self.error
