"""Result of building a motion stack (no anonymous tuples)."""

from __future__ import annotations

from dataclasses import dataclass

from lib.rover_motion_client import RoverMotionClient
from lib.yahboom_drive_board import YahboomDriveBoard


@dataclass
class MotionStackBundle:
  """Motion client plus optional Yahboom board handle (IMU / close)."""

  client: RoverMotionClient
  yahboom_board: YahboomDriveBoard | None = None
