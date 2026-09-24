"""Battery voltage reading from the Hiwonder ADC register."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryReading:
  """Supply voltage reported by the motor driver."""

  millivolts: int = 0
