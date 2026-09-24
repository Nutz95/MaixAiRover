"""DBG panel actions for the Yahboom USB board."""

from __future__ import annotations

from enum import Enum


class YahboomDebugAction(Enum):
  """Named Yahboom debug-panel actions (no magic strings at call sites)."""

  POLL = "poll"
  STOP = "stop"
  FWD = "fwd"
  INIT = "init"
