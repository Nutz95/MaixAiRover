#!/usr/bin/env python3
"""Host Tk debug cockpit for Yahboom ROS board (no MaixCAM required)."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
  sys.path.insert(0, str(_TOOLS))

from yahboom_debug.app import YahboomDebugApp


def main() -> int:
  """Launch the Yahboom debug UI; Ctrl+C exits without a traceback spam."""
  app = YahboomDebugApp()
  try:
    return app.run()
  except KeyboardInterrupt:
    try:
      app.shutdown()
    except Exception:
      pass
    print("\nbye (Ctrl+C)")
    return 0


if __name__ == "__main__":
  raise SystemExit(main())
