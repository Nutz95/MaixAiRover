"""DBG panel actions for the ESP link pump."""

from __future__ import annotations

from enum import Enum


class EspDebugAction(str, Enum):
  """Named debug-panel actions (no magic strings at call sites)."""

  PING = "ping"
  STOP = "stop"
  FWD = "fwd"
  INIT = "init"
