"""Tk debug cockpit: Yahboom board + Xbox pad (PC host, no MaixCAM)."""

from __future__ import annotations

import os
import signal
import tkinter as tk
from tkinter import ttk

from yahboom_debug.board_session import YahboomBoardSession
from yahboom_debug.gamepad_tab import GamepadTab
from yahboom_debug.motors_tab import MotorsTab

_BG = "#1e1e2e"
_FG = "#cdd6f4"
_MUTED = "#a6adc8"
_GREEN = "#40a02b"
_GREEN_BG = "#1a3d2a"
_RED = "#d20f39"
_RED_BG = "#3d1a1a"
_ORANGE = "#fe640b"
_ORANGE_BG = "#3d2a1a"
_ACCENT = "#89b4fa"


class YahboomDebugApp:
  """Two-tab host debugger: gamepad mapping + per-motor open-loop."""

  def __init__(self) -> None:
    """Build window, board session, and notebooks."""
    self._root = tk.Tk()
    self._root.title("Yahboom debug — gamepad + motors")
    self._root.geometry("920x820")
    self._root.minsize(780, 640)
    self._root.configure(bg=_BG)
    self._root.protocol("WM_DELETE_WINDOW", self._on_close)
    self._session = YahboomBoardSession()
    self._port = tk.StringVar(
      value=os.environ.get("YAHBOOM_DEBUG_PORT", "COM15").strip() or "COM15",
    )
    self._conn_text = tk.StringVar(value="DISCONNECTED")
    self._conn_detail = tk.StringVar(value="Click Connect — USB Micro « Connect USB » + DC ON")
    self._bat_text = tk.StringVar(value="battery: —")
    self._alive = True
    self._bat_n = 0
    self._outer_prev = 0
    self._style()
    self._build()
    self._set_link_state("disconnected")
    self._root.after(50, self._tick)

  def _style(self) -> None:
    style = ttk.Style(self._root)
    try:
      style.theme_use("clam")
    except tk.TclError:
      pass
    style.configure(".", background=_BG, foreground=_FG, fieldbackground="#313244")
    style.configure("TFrame", background=_BG)
    style.configure("TLabel", background=_BG, foreground=_FG)
    style.configure("TButton", padding=6)
    style.configure("TNotebook", background=_BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(12, 6), background="#313244", foreground=_FG)
    style.map("TNotebook.Tab", background=[("selected", "#45475a")])
    style.configure("TLabelframe", background=_BG, foreground=_ACCENT)
    style.configure("TLabelframe.Label", background=_BG, foreground=_ACCENT)
    style.configure("TCheckbutton", background=_BG, foreground=_FG)
    style.configure("TEntry", fieldbackground="#313244", foreground=_FG)
    style.configure("Horizontal.TScale", background=_BG)

  def _build(self) -> None:
    # Big connection banner (always visible).
    self._banner = tk.Frame(self._root, bg=_RED_BG, padx=12, pady=10)
    self._banner.pack(fill=tk.X)
    self._banner_dot = tk.Canvas(
      self._banner, width=18, height=18, bg=_RED_BG, highlightthickness=0,
    )
    self._banner_dot.pack(side=tk.LEFT, padx=(0, 10))
    self._dot_id = self._banner_dot.create_oval(2, 2, 16, 16, fill=_RED, outline="")
    titles = tk.Frame(self._banner, bg=_RED_BG)
    titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
    self._banner_title = tk.Label(
      titles, textvariable=self._conn_text, bg=_RED_BG, fg=_RED,
      font=("Segoe UI", 14, "bold"), anchor="w",
    )
    self._banner_title.pack(fill=tk.X)
    self._banner_sub = tk.Label(
      titles, textvariable=self._conn_detail, bg=_RED_BG, fg=_MUTED,
      font=("Segoe UI", 9), anchor="w",
    )
    self._banner_sub.pack(fill=tk.X)
    self._bat_label = tk.Label(
      self._banner, textvariable=self._bat_text, bg=_RED_BG, fg=_MUTED,
      font=("Consolas", 11),
    )
    self._bat_label.pack(side=tk.RIGHT)

    bar = ttk.Frame(self._root, padding=8)
    bar.pack(fill=tk.X)
    ttk.Label(bar, text="COM").pack(side=tk.LEFT)
    ttk.Entry(bar, textvariable=self._port, width=10).pack(side=tk.LEFT, padx=4)
    ttk.Button(bar, text="Connect", command=self._connect).pack(side=tk.LEFT)
    ttk.Button(bar, text="Disconnect", command=self._disconnect).pack(side=tk.LEFT, padx=4)
    stop = tk.Button(
      bar, text="STOP ALL", command=self._estop,
      bg=_RED, fg="white", activebackground="#a00", font=("Segoe UI", 10, "bold"),
      padx=10, pady=4, relief=tk.FLAT,
    )
    stop.pack(side=tk.LEFT, padx=10)
    ttk.Button(bar, text="Beep", command=self._beep).pack(side=tk.LEFT)

    self._notebook = ttk.Notebook(self._root)
    self._notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    self._gamepad = GamepadTab(self._notebook, self._session)
    self._motors = MotorsTab(self._notebook, self._session)
    self._notebook.add(self._gamepad.frame, text="Gamepad")
    self._notebook.add(self._motors.frame, text="Motors")
    self._notebook.bind("<<NotebookTabChanged>>", self._on_outer_tab)

    tk.Label(
      self._root,
      text="PC-only · Micro-USB data · DC 6–13 V for motors · no MaixCAM",
      bg=_BG, fg=_MUTED, anchor="w", padx=10, pady=6,
    ).pack(fill=tk.X)

  def _set_link_state(self, state: str, detail: str = "") -> None:
    """Update the coloured banner: connected | disconnected | error | stopped."""
    if state == "connected":
      bg, fg, title = _GREEN_BG, _GREEN, "CONNECTED"
      port = self._session.port or self._port.get()
      detail = detail or f"Board online on {port}"
    elif state == "stopped":
      bg, fg, title = _ORANGE_BG, _ORANGE, "CONNECTED — MOTORS STOPPED"
      detail = detail or "E-stop sent; link still open"
    elif state == "error":
      bg, fg, title = _RED_BG, _RED, "CONNECTION FAILED"
      detail = detail or "Check COM port / cable / board power"
    else:
      bg, fg, title = _RED_BG, _RED, "DISCONNECTED"
      detail = detail or "Click Connect — USB Micro « Connect USB » + DC ON"
    self._conn_text.set(title)
    self._conn_detail.set(detail)
    for widget in (self._banner, self._banner_title, self._banner_sub, self._bat_label):
      widget.configure(bg=bg)
    self._banner_title.configure(fg=fg)
    self._banner_sub.configure(fg=_MUTED if state != "error" else _RED)
    self._bat_label.configure(bg=bg, fg=_MUTED)
    self._banner_dot.configure(bg=bg)
    self._banner_dot.itemconfigure(self._dot_id, fill=fg)

  def _connect(self) -> None:
    port = self._port.get().strip()
    self._set_link_state("disconnected", f"Connecting to {port}…")
    self._root.update_idletasks()
    try:
      self._session.connect(port)
      ctype = self._session.car_type
      reported = self._session.car_type_reported
      names = {1: "X3 mecanum", 2: "X3PLUS", 4: "X1", 5: "R2"}
      detail = (
        f"{port} · car_type={ctype} ({names.get(ctype, '?')})"
        f" · MCU reports {reported}"
      )
      self._set_link_state("connected", detail)
      self._refresh_battery()
      self._session.beep(60)
    except Exception as connect_error:
      self._set_link_state("error", str(connect_error))
      self._bat_text.set("battery: —")

  def _disconnect(self) -> None:
    self._gamepad.on_leave()
    self._motors.on_leave()
    self._session.disconnect()
    self._set_link_state("disconnected", "Serial closed — safe to reconnect")
    self._bat_text.set("battery: —")

  def _estop(self) -> None:
    self._gamepad.on_leave()
    self._motors.on_leave()
    if self._session.connected:
      try:
        self._session.stop_all()
        self._set_link_state("stopped")
      except Exception as stop_error:
        self._set_link_state("error", f"STOP failed: {stop_error}")
    else:
      self._set_link_state("disconnected", "STOP ignored — not connected")

  def _beep(self) -> None:
    if not self._session.connected:
      self._set_link_state("disconnected", "Beep ignored — not connected")
      return
    try:
      self._session.beep(100)
    except Exception as beep_error:
      self._set_link_state("error", f"beep: {beep_error}")

  def _refresh_battery(self) -> None:
    if not self._session.connected:
      return
    try:
      volts = self._session.battery_v()
      colour_note = ""
      if volts < 6.0:
        colour_note = " ⚠ LOW — motors need DC IN"
      self._bat_text.set(f"battery: {volts:.1f} V{colour_note}")
    except Exception as bat_error:
      self._bat_text.set(f"battery: err {bat_error}")

  def _on_outer_tab(self, _event=None) -> None:
    current = self._notebook.index(self._notebook.select())
    if self._outer_prev == 0 and current != 0:
      self._gamepad.on_leave()
    if self._outer_prev == 1 and current != 1:
      self._motors.on_leave()
    self._outer_prev = current

  def _tick(self) -> None:
    if not self._alive:
      return
    # Detect surprise disconnect (unplug).
    if self._session.reclaim_if_dead():
      self._set_link_state("error", "Link lost — serial closed")
      self._bat_text.set("battery: —")
    if self._notebook.index(self._notebook.select()) == 0:
      self._gamepad.tick()
    self._bat_n += 1
    if self._bat_n >= 30:
      self._bat_n = 0
      self._refresh_battery()
    self._root.after(33, self._tick)

  def _on_close(self) -> None:
    if not self._alive:
      return
    self._alive = False
    try:
      self._gamepad.shutdown()
      self._motors.on_leave()
      self._session.disconnect()
    except Exception as close_error:
      print(f"ui close: {close_error}")
    try:
      self._root.destroy()
    except tk.TclError:
      pass

  def shutdown(self) -> None:
    """Public stop for Ctrl+C / launcher."""
    self._on_close()

  def run(self) -> int:
    """Block on Tk mainloop; Ctrl+C closes cleanly."""
    def _sigint(_signum, _frame) -> None:
      try:
        self._root.after(0, self._on_close)
      except tk.TclError:
        pass

    try:
      signal.signal(signal.SIGINT, _sigint)
    except Exception as sig_error:
      print(f"ui: signal handler: {sig_error}")
    try:
      self._root.mainloop()
    except KeyboardInterrupt:
      self._on_close()
    return 0
