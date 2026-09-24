"""Compose camera / checklist / DBG frames for display.show."""

from __future__ import annotations

from maix import image


class HudComposer:
  """Build one display frame without USB I/O on the draw path."""

  def __init__(self, app_ref) -> None:
    """Bind to XboxRoverApp for panels, camera, and cached instruments."""
    self._app = app_ref

  def draw(self) -> None:
    """Draw checklist, DBG, or teleop HUD and call display.show."""
    a = self._app
    with a._checklist_lock:
      checklist_open = a._checklist_open
      checklist = a._checklist
    debug_open = False
    debug_link = ""
    debug_status = ""
    debug_telem = None
    yahboom_snap = None
    if a._yahboom_debug is not None and a._yahboom_debug.is_open():
      yahboom_snap = a._yahboom_debug.snapshot()
      debug_open = True
    elif a._debug is not None and a._debug.is_open():
      snap_dbg = a._debug.snapshot()
      debug_open = True
      debug_link = snap_dbg.link_name
      debug_status = snap_dbg.status
      debug_telem = snap_dbg.telem

    if checklist_open:
      frame = image.Image(a._disp.width(), a._disp.height(), bg=image.COLOR_BLACK)
      a._checklist_panel.draw(frame, checklist)
      a._disp.show(frame)
      return

    if debug_open:
      frame = image.Image(a._disp.width(), a._disp.height(), bg=image.COLOR_BLACK)
      if yahboom_snap is not None:
        a._yahboom_debug_panel.draw(frame, yahboom_snap)
      else:
        a._debug_panel.draw(
          frame, link_name=debug_link, status=debug_status, telem=debug_telem,
        )
      a._disp.show(frame)
      return

    frame = None
    if a._camera is not None:
      frame = a._camera.get_frame()
    if frame is None:
      frame = image.Image(a._disp.width(), a._disp.height(), bg=image.COLOR_BLACK)
    else:
      frame = self._drawable_rgb(frame)
    snap = a._xbox.snapshot()
    ball_snap = a._ball.snapshot()
    a._ball.draw_depth(frame)
    wheels = a._rover.last_wheel_speeds()
    a._ui.draw_overlay(
      frame,
      snap.connected,
      snap.busy,
      snap.state,
      snap.drive,
      a._session_max_speed,
      status=snap.status,
      progress=snap.progress,
      instruments=a._hud_instruments(),
      wheel_fl=wheels.front_left,
      wheel_fr=wheels.front_right,
      motor_limit=a._motor_limit,
      ball_snapshot=ball_snap,
    )
    a._disp.show(frame)

  @staticmethod
  def _drawable_rgb(frame):
    """Return an RGB888 image MaixPy can draw on."""
    try:
      fmt = frame.format()
    except Exception as format_error:
      print(f"hud: frame.format: {format_error}")
      return frame
    if fmt in (image.Format.FMT_RGB888, image.Format.FMT_BGR888):
      return frame
    try:
      return frame.to_format(image.Format.FMT_RGB888)
    except Exception as convert_error:
      print(f"hud: cannot convert frame ({convert_error}); RGB blank")
      return image.Image(frame.width(), frame.height(), bg=image.COLOR_BLACK)
