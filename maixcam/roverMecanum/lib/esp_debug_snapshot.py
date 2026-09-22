"""Immutable snapshot of ESP debug-panel UI state."""

from __future__ import annotations

from dataclasses import dataclass

from lib.telem_snapshot import TelemSnapshot


@dataclass(frozen=True)
class EspDebugSnapshot:
  """Panel visibility + link status + latest TELEM."""

  panel_open: bool
  link_name: str
  status: str
  telem: TelemSnapshot | None
