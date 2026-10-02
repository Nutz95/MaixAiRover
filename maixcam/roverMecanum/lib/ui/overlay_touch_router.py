"""Touch routing for checklist / DBG / pair / exit overlays."""

from __future__ import annotations

from maix import time

from lib.esp.esp_debug_action import EspDebugAction
from lib.yahboom.yahboom_debug_action import YahboomDebugAction


class OverlayTouchRouter:
  """Map one TouchPoint to checklist, debug, pair, or exit actions."""

  def __init__(self, app_ref) -> None:
    """Hold a back-reference to XboxRoverApp for UI rects and sessions."""
    self._app = app_ref

  def handle(self, action) -> None:
    """Dispatch one latched touch to the active overlay or main HUD."""
    a = self._app
    if a._drive_link_open:
      if a._drive_link_panel.retry_rect().contains(action.x, action.y):
        a.retry_drive_link()
      elif a._ui.back_rect().contains(action.x, action.y):
        a._request_exit()
      return

    with a._checklist_lock:
      checklist_open = a._checklist_open
      checklist_ready = a._checklist is not None
    debug_open = (
      (a._yahboom_debug is not None and a._yahboom_debug.is_open())
      or (a._debug is not None and a._debug.is_open())
    )

    if checklist_open:
      if checklist_ready and a._checklist_panel.ok_rect().contains(action.x, action.y):
        a._overlays.close_checklist()
      elif a._ui.back_rect().contains(action.x, action.y):
        a._request_exit()
      return

    if a._obstacle is not None and a._obstacle.is_calib_open():
      panel = a._obstacle.calib_panel
      if panel.ok_rect().contains(action.x, action.y):
        a._overlays.handle_modal_confirm()
      elif panel.skip_rect().contains(action.x, action.y):
        if a._obstacle.skip_calib():
          if a._camera is not None and (
            not a._obstacle.is_calib_open() or a._obstacle.uses_live_camera()
          ):
            a._camera.set_paused(False)
          a._arm_touch_ignore()
      elif a._ui.back_rect().contains(action.x, action.y):
        a._request_exit()
      return

    if debug_open and a._yahboom_debug is not None:
      panel = a._yahboom_debug_panel
      if panel.close_rect().contains(action.x, action.y):
        a._overlays.close_debug()
      elif panel.poll_rect().contains(action.x, action.y):
        a._yahboom_debug.run_action(YahboomDebugAction.POLL)
      elif panel.stop_rect().contains(action.x, action.y):
        a._yahboom_debug.run_action(YahboomDebugAction.STOP)
      elif panel.fwd_rect().contains(action.x, action.y):
        a._yahboom_debug.run_action(YahboomDebugAction.FWD)
      elif panel.init_rect().contains(action.x, action.y):
        a._yahboom_debug.run_action(YahboomDebugAction.INIT)
      return

    if debug_open and a._debug is not None:
      if a._debug_panel.close_rect().contains(action.x, action.y):
        a._overlays.close_debug()
      elif a._debug_panel.ping_rect().contains(action.x, action.y):
        a._debug.run_action(EspDebugAction.PING)
      elif a._debug_panel.stop_rect().contains(action.x, action.y):
        a._debug.run_action(EspDebugAction.STOP)
      elif a._debug_panel.fwd_rect().contains(action.x, action.y):
        a._debug.run_action(EspDebugAction.FWD)
      elif a._debug_panel.init_rect().contains(action.x, action.y):
        a._debug.run_action(EspDebugAction.INIT)
      return

    snap = a._xbox.snapshot()
    if a._ui.back_rect().contains(action.x, action.y):
      a._request_exit()
      return
    if not snap.busy and not snap.connected:
      if a._ui.pair_rect().contains(action.x, action.y):
        a._xbox.start_pairing()
      elif a._ui.connect_rect().contains(action.x, action.y):
        a._xbox.start_connect()
      return
    ball_follow_on = False
    try:
      ball_follow_on = bool(a._ball.snapshot().enabled)
    except Exception as ball_snap_error:
      print(f"touch: ball snapshot: {ball_snap_error}")
    if ball_follow_on:
      return
    # DBG/DISC HUD buttons removed — use Xbox X / B.
