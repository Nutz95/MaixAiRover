"""Yahboom pack voltage from auto-report speed frames."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YahboomBattery:
  """Battery sample from ``FUNC_REPORT_SPEED`` (tenths of a volt on wire)."""

  volts: float

  @property
  def millivolts(self) -> int:
    """Voltage in millivolts."""
    return int(round(self.volts * 1000.0))
