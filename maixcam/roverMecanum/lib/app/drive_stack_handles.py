"""Typed handles returned when loading the drive backend."""

from __future__ import annotations

from dataclasses import dataclass

from lib.esp.esp_debug_session import EspDebugSession
from lib.motion.drive_backend_kind import DriveBackendKind
from lib.motion.rover_motion_client import RoverMotionClient
from lib.yahboom.yahboom_debug_session import YahboomDebugSession
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard


@dataclass
class DriveStackHandles:
  """Typed motion backend handles for the app."""

  kind: DriveBackendKind
  rover: RoverMotionClient
  yahboom_board: YahboomDriveBoard | None
  yahboom_debug: YahboomDebugSession | None
  esp_front_debug: EspDebugSession | None
  esp_rear_debug: EspDebugSession | None
