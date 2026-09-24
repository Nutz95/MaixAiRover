"""Parsed bluetoothctl scan match (exact / partial / count)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BluetoothScanMatch:
  """Result of matching bluetoothctl device listings against name targets."""

  exact_mac: str | None
  partial_mac: str | None
  devices_seen: int
