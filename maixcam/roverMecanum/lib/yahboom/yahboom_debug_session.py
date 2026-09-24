"""Yahboom debug panel session over an open drive board."""

from __future__ import annotations

from lib.motion.chassis_velocity import ChassisVelocity
from lib.yahboom.yahboom_debug_action import YahboomDebugAction
from lib.yahboom.yahboom_debug_snapshot import YahboomDebugSnapshot
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard

# Gentle closed-loop crawl for FWD smoke (m/s).
_FWD_VX = 0.25


class YahboomDebugSession:
  """Owns DBG open/close + board smoke actions (STOP / FWD / POLL / INIT)."""

  def __init__(self, board: YahboomDriveBoard) -> None:
    self._board = board
    self._panel_open = False
    self._status = "ready"

  def is_open(self) -> bool:
    """True while the Yahboom debug panel should be shown."""
    return self._panel_open

  def open(self) -> None:
    """Show the debug panel."""
    self._panel_open = True
    self._status = "ready"
    self._board.poll()

  def close(self) -> None:
    """Hide the panel and stop the chassis."""
    self._panel_open = False
    try:
      self._board.stop()
    except Exception as exc:
      print(f"yahboom dbg stop: {exc}")
    self._status = "closed"

  def snapshot(self) -> YahboomDebugSnapshot:
    """One RX pump then cached sensors (call only while panel is open)."""
    self._board.poll()
    return YahboomDebugSnapshot(
      panel_open=self._panel_open,
      status=self._status,
      battery=self._board.battery(),
      imu=self._board.imu_attitude(),
      encoders=self._board.read_encoders(),
    )

  def run_action(self, action: YahboomDebugAction) -> None:
    """Run one DBG button action on the board."""
    if action is YahboomDebugAction.POLL:
      self._board.poll()
      self._status = "POLL ok"
      return
    if action is YahboomDebugAction.STOP:
      self._board.stop()
      self._status = "STOP"
      return
    if action is YahboomDebugAction.FWD:
      self._board.set_velocity(ChassisVelocity(vx=_FWD_VX))
      self._status = f"FWD {_FWD_VX:.2f} m/s"
      return
    if action is YahboomDebugAction.INIT:
      self._board.refresh_reports()
      self._status = "INIT reports"
      return
    raise ValueError(f"unknown YahboomDebugAction: {action}")
