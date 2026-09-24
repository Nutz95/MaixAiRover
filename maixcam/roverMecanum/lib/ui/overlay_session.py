"""Checklist and DBG overlay open/close + peripheral probe thread."""

from __future__ import annotations

import threading


class OverlaySession:
  """Own checklist/debug modal state for the main HUD."""

  def __init__(self, app_ref) -> None:
    """Bind to XboxRoverApp fields used by overlays."""
    self._app = app_ref

  def on_connection_change(self) -> None:
    """Open checklist on connect; tear down overlays on disconnect."""
    a = self._app
    snap = a._xbox.snapshot()
    if snap.connected and not a._was_connected:
      self.open_checklist()
      threading.Thread(
        target=self.run_peripheral_checklist, daemon=True, name="periph-check",
      ).start()
    if not snap.connected and a._was_connected:
      self.close_checklist()
      self.close_debug()
      if a._debug is not None:
        a._debug.stop_link()
      if a._rear_debug is not None:
        a._rear_debug.stop_link()
    if snap.connected != a._was_connected or snap.busy != a._was_busy:
      a._arm_touch_ignore()
    a._was_connected = snap.connected
    a._was_busy = snap.busy

  def open_checklist(self) -> None:
    a = self._app
    with a._checklist_lock:
      a._checklist = None
      a._checklist_open = True
    if a._camera is not None:
      a._camera.set_paused(True)

  def close_checklist(self) -> None:
    a = self._app
    with a._checklist_lock:
      a._checklist_open = False
      a._checklist = None
    a._arm_touch_ignore()
    if a._xbox.snapshot().connected:
      if a._debug is not None:
        a._debug.start_link()
      if a._rear_debug is not None:
        a._rear_debug.start_link()
    debug_open = (
      (a._yahboom_debug is not None and a._yahboom_debug.is_open())
      or (a._debug is not None and a._debug.is_open())
    )
    if a._camera is not None and not debug_open:
      a._camera.set_paused(False)

  def open_debug(self) -> None:
    a = self._app
    if a._yahboom_debug is not None:
      if a._camera is not None:
        a._camera.set_paused(True)
      a._yahboom_debug.open()
      a._arm_touch_ignore()
      return
    if a._debug is None:
      return
    if a._camera is not None:
      a._camera.set_paused(True)
    a._debug.open()
    a._arm_touch_ignore()

  def close_debug(self) -> None:
    a = self._app
    was_open = False
    if a._yahboom_debug is not None and a._yahboom_debug.is_open():
      a._yahboom_debug.close()
      was_open = True
    elif a._debug is not None and a._debug.is_open():
      a._debug.close()
      was_open = True
    if was_open:
      a._arm_touch_ignore()
    if was_open and a._camera is not None and not a._checklist_open:
      a._camera.set_paused(False)

  def run_peripheral_checklist(self) -> None:
    """Probe Yahboom or ESP after pad connect; fill the opaque checklist panel."""
    a = self._app
    report = a._health.run(
      xbox_connected=True,
      camera_ok=a._camera is not None,
      motion_is_stub=a._rover.is_stub(),
      yahboom_board=a._yahboom_board,
    )
    print("peripheral checklist:")
    for line in report.log_lines():
      print(f"  {line}")
    with a._checklist_lock:
      if a._checklist_open:
        a._checklist = report
