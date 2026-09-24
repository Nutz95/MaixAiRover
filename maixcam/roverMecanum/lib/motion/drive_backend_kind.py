"""Which motion stack the Maix app builds."""

from __future__ import annotations

from enum import Enum


class DriveBackendKind(str, Enum):
  """Motion backend selector (``config.json`` ``drive_backend``)."""

  ESP = "esp"
  YAHBOOM = "yahboom"
