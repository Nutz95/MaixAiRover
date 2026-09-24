"""Snapshot of Xbox input service state for the UI and control loop."""

from dataclasses import dataclass
from typing import Optional

from lib.input.controller_state import ControllerState
from lib.input.drive_output import DriveOutput


@dataclass(frozen=True)
class XboxSnapshot:
  """Immutable view of controller connection and mapped drive output."""

  status: str
  connected: bool
  busy: bool
  state: ControllerState
  drive: Optional[DriveOutput]
  progress: float = 0.0
