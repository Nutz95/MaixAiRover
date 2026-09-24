"""High-rate Xbox → mecanum drive thread (separate from HUD)."""

from __future__ import annotations

import threading

from maix import app, time


class TeleopControlThread:
  """Poll pad + push wheel setpoints on a dedicated thread (~100 Hz)."""

  def __init__(
    self,
    *,
    xbox,
    rover,
    send_drive,
    send_interval_ms: int = 10,
    on_tick=None,
  ) -> None:
    self._xbox = xbox
    self._rover = rover
    self._send_drive = send_drive
    self._send_interval_ms = max(5, send_interval_ms)
    self._on_tick = on_tick
    self._stop = threading.Event()
    self._thread: threading.Thread | None = None

  def set_send_interval_ms(self, ms: int) -> None:
    """Update teleop send cadence (ms)."""
    self._send_interval_ms = max(5, ms)

  def start(self) -> None:
    """Start the control thread."""
    if self._thread is not None and self._thread.is_alive():
      return
    self._stop.clear()
    self._thread = threading.Thread(target=self._run, daemon=True, name="teleop-ctrl")
    self._thread.start()

  def stop(self) -> None:
    """Stop the control thread and wait for it to leave the drive path."""
    self._stop.set()
    if self._thread is not None:
      self._thread.join(timeout=2.0)
      if self._thread.is_alive():
        print("teleop-ctrl: stop join timed out")
      else:
        self._thread = None

  def _run(self) -> None:
    send_ms = 0
    was_connected = False
    while not self._stop.is_set() and not app.need_exit():
      if self._on_tick is not None:
        self._on_tick()
      self._xbox.poll()
      snap = self._xbox.snapshot()
      now = time.ticks_ms()
      if snap.connected and snap.drive is not None and now - send_ms >= self._send_interval_ms:
        self._send_drive(snap.drive)
        send_ms = now
      elif was_connected and not snap.connected:
        try:
          self._rover.send_stop()
        except Exception as stop_error:
          print(f"teleop-ctrl: send_stop on disconnect: {stop_error}")
      was_connected = snap.connected
      # Yield GIL so HUD can draw; send_interval (~15ms) still bounds motor lag.
      time.sleep_ms(6)
