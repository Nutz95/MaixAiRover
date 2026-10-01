"""pytest configuration for MaixAiRover host tests."""

from __future__ import annotations

import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_LIB_ROOT = os.path.abspath(os.path.join(_TESTS, "..", "maixcam", "roverMecanum"))

for path in (_TESTS, _LIB_ROOT):
  if path not in sys.path:
    sys.path.insert(0, path)
