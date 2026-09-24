"""Ordered peripheral health report after controller connect."""

from dataclasses import dataclass
from typing import List

from lib.health.peripheral_check import PeripheralCheck


@dataclass(frozen=True)
class PeripheralChecklist:
  """Immutable list of peripheral checks for HUD and console."""

  checks: List[PeripheralCheck]

  def all_ok(self) -> bool:
    """True when every check passed."""
    return all(item.ok for item in self.checks)

  def log_lines(self) -> List[str]:
    """Return printable lines for the console."""
    return [item.format_line() for item in self.checks]
