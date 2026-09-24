"""MaixCAM2 battery percent from CW2015 sysfs."""

from __future__ import annotations

import os


class MaixBatteryReader:
  """Read ``cw2015-battery`` capacity (MaixCAM2 fuel gauge)."""

  DEFAULT_PATH = "/sys/class/power_supply/cw2015-battery/capacity"

  def __init__(self, capacity_path: str = DEFAULT_PATH) -> None:
    self._path = capacity_path

  def percent(self) -> int | None:
    """Return SoC 0..100, or None if sysfs is missing/unreadable."""
    try:
      with open(self._path, encoding="utf-8") as handle:
        raw = handle.read().strip()
      value = int(raw)
    except (OSError, ValueError):
      return None
    return max(0, min(100, value))
