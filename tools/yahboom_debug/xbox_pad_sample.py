"""Normalized Xbox pad sample for the host debug UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class XboxPadSample:
  """Deadzoned sticks/triggers in [-1, 1] plus hat/buttons."""

  left_x: float
  left_y: float
  right_x: float
  right_y: float
  lt: float
  rt: float
  hat_x: int  # -1 left, 0, +1 right
  hat_y: int  # -1 up, 0, +1 down (pygame)
  button_a: bool
  name: str
