"""Single-threaded ESP binary pump: drive fire-and-forget, telem only when idle."""

from __future__ import annotations

import threading
import time

from lib.esp_binary_client import EspBinaryClient
from lib.esp_binary_protocol import CMD_PWM, CMD_SPEED, CMD_STOP
from lib.esp_debug_action import EspDebugAction
from lib.esp_debug_snapshot import EspDebugSnapshot
from lib.esp_drive_cmd import EspDriveCmd
from lib.telem_snapshot import TelemSnapshot


class EspLinkPump:
  """One UART owner. Latest drive wins; TELEM never blocks a pending drive."""

  TELEM_IDLE_MS = 250
  TELEM_PANEL_MS = 100
  TELEM_SLICE_S = 0.008
  TELEM_ACK_S = 0.10

  def __init__(self, uart_port: str = "uart4") -> None:
    self._uart_port = uart_port
    self._lock = threading.Lock()
    self._client: EspBinaryClient | None = None
    self._link = ""
    self._status = ""
    self._telem: TelemSnapshot | None = None
    self._drive: EspDriveCmd | None = None
    self._drive_dirty = False
    self._panel_open = False
    self._wanted = False
    self._stop = threading.Event()
    self._exit = threading.Event()
    self._alive = False
    self._dbg_action: EspDebugAction | None = None
    self._wake = threading.Event()
    self._stop_acked = False

  def snapshot(self) -> EspDebugSnapshot:
    """Return panel visibility, link name, status, and latest TELEM."""
    with self._lock:
      return EspDebugSnapshot(
        panel_open=self._panel_open,
        link_name=self._link,
        status=self._status,
        telem=self._telem,
      )

  def telem(self) -> TelemSnapshot | None:
    """Latest TELEM (may be None)."""
    with self._lock:
      return self._telem

  def binary_client(self) -> EspBinaryClient | None:
    """Raw client (DBG INIT); teleop must use ``set_drive``."""
    with self._lock:
      return self._client

  def is_panel_open(self) -> bool:
    """True while DBG panel should show."""
    with self._lock:
      return self._panel_open

  def start(self) -> None:
    """Open link + pump thread if needed."""
    with self._lock:
      self._wanted = True
      if self._alive:
        return
      self._alive = True
      self._status = "opening…"
    self._stop.clear()
    self._wake.set()
    threading.Thread(target=self._run, daemon=True, name="esp-pump").start()

  def stop(self) -> None:
    """Close link and stop the pump."""
    with self._lock:
      self._wanted = False
      self._panel_open = False
    self._stop.set()
    self._wake.set()
    with self._lock:
      self._status = ""
      self._telem = None
      client = self._client
      self._client = None
    if client is not None:
      try:
        client.close()
      except Exception:
        pass

  def set_panel_open(self, open_: bool) -> None:
    """Show/hide DBG panel; starts the pump when opening."""
    with self._lock:
      self._panel_open = bool(open_)
    if open_:
      self.start()
    self._wake.set()

  def set_drive(self, fl: int, fr: int) -> None:
    """Queue latest FL/FR (non-blocking). ``(0,0)`` becomes STOP."""
    with self._lock:
      if fl == 0 and fr == 0:
        self._drive = EspDriveCmd(0, 0, stop=True)
      else:
        self._drive = EspDriveCmd(int(fl), int(fr), stop=False)
      self._drive_dirty = True
    self._wake.set()

  def queue_dbg(self, action: EspDebugAction) -> None:
    """Queue one DBG button action."""
    with self._lock:
      self._dbg_action = action
    self._wake.set()

  def shutdown(self) -> None:
    """App exit."""
    self._exit.set()
    self.stop()

  def _has_drive(self) -> bool:
    with self._lock:
      return self._drive_dirty

  def _run(self) -> None:
    client = EspBinaryClient(uart_port=self._uart_port)
    try:
      client.open()
    except Exception as exc:
      with self._lock:
        self._status = f"link fail: {exc}"
        self._link = ""
        self._alive = False
      return
    with self._lock:
      self._client = client
      self._link = client.link_name
      self._status = "ready"
    last_telem_ms = 0.0
    while not self._stop.is_set() and not self._exit.is_set():
      with self._lock:
        if not self._wanted and not self._panel_open:
          break
        panel = self._panel_open
        drive = self._drive if self._drive_dirty else None
        if self._drive_dirty:
          self._drive_dirty = False
        dbg = self._dbg_action
        self._dbg_action = None
      try:
        if dbg is not None:
          self._do_dbg(client, dbg)
          continue
        if drive is not None:
          self._do_drive_fast(client, drive)
          last_telem_ms = time.time() * 1000.0
          continue
        interval = self.TELEM_PANEL_MS if panel else self.TELEM_IDLE_MS
        now = time.time() * 1000.0
        if now - last_telem_ms >= interval:
          snap = self._telem_abortable(client)
          if snap is not None:
            with self._lock:
              self._telem = snap
              if panel:
                self._status = "telem ok"
            last_telem_ms = time.time() * 1000.0
          continue
        self._wake.wait(0.004)
        self._wake.clear()
      except Exception as exc:
        with self._lock:
          self._status = str(exc)[:48]
        time.sleep(0.01)
    try:
      client.close()
    except Exception:
      pass
    with self._lock:
      if self._client is client:
        self._client = None
      self._alive = False
      self._link = ""

  def _do_drive_fast(self, client: EspBinaryClient, drive: EspDriveCmd) -> None:
    """SPEED fire-and-forget; first STOP after motion waits for ACK, then FAF."""
    if drive.stop:
      if not self._stop_acked:
        try:
          client.stop(timeout_s=0.04)
        except Exception:
          client.write_frame(CMD_STOP, b"")
          client.drain(max_s=0.008)
        self._stop_acked = True
      else:
        client.write_frame(CMD_STOP, b"")
        client.drain(max_s=0.003)
      return
    self._stop_acked = False
    client.write_speed(drive.fl, drive.fr, 0, 0)
    client.drain(max_s=0.003)

  def _telem_abortable(self, client: EspBinaryClient) -> TelemSnapshot | None:
    """TELEM request that yields immediately if a drive setpoint arrives."""
    if self._has_drive():
      return None
    client.write_telem()
    deadline = time.time() + self.TELEM_ACK_S
    while time.time() < deadline:
      if self._has_drive() or self._stop.is_set():
        client.drain(max_s=0.002)
        return None
      snap = client.poll_telem(max_s=self.TELEM_SLICE_S)
      if snap is not None:
        return snap
    client.drain(max_s=0.002)
    return None

  def _do_dbg(self, client: EspBinaryClient, action: EspDebugAction) -> None:
    try:
      if action is EspDebugAction.PING:
        client.ping(timeout_s=0.25)
        msg = "PING ok"
      elif action is EspDebugAction.STOP:
        client.write_frame(CMD_STOP, b"")
        client.drain(max_s=0.02)
        msg = "STOP ok"
      elif action is EspDebugAction.FWD:
        client.write_speed(20, 20, 0, 0)
        client.drain(max_s=0.02)
        msg = "SPEED 20 20"
      elif action is EspDebugAction.INIT:
        msg = client.text_command("INIT")
      else:
        msg = f"unknown {action}"
      with self._lock:
        self._status = msg
    except Exception as exc:
      with self._lock:
        self._status = f"{action.value}: {exc}"
