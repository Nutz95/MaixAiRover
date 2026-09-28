"""Motors notebook: one unit-test tab per Yahboom channel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from yahboom_debug.board_session import YahboomBoardSession
from yahboom_debug.motor_panel import MotorPanel


class MotorsTab:
  """Sub-tabs M1..M4 for connector / direction checks."""

  def __init__(self, parent, session: YahboomBoardSession) -> None:
    """Build nested notebook of motor panels."""
    self._session = session
    self._frame = ttk.Frame(parent, padding=4)
    ttk.Label(
      self._frame,
      justify=tk.LEFT,
      text=(
        "Firmware corners: M1=FL M2=RL M3=FR M4=RR (left side first — Yahboom docs §12/§15).\n"
        "Open-loop tabs drive connector Mi. If a tab moves another wheel → move that plug.\n"
        "Calibrate: +PWM = robot-FORWARD + encoder UP on that corner."
      ),
    ).pack(anchor=tk.W, pady=(0, 6))
    self._panels: list[MotorPanel] = []
    self._notebook = ttk.Notebook(self._frame)
    self._notebook.pack(fill=tk.BOTH, expand=True)
    for index, label in enumerate(YahboomBoardSession.MOTOR_LABELS, start=1):
      panel = MotorPanel(self._notebook, session, index, label)
      self._panels.append(panel)
      self._notebook.add(panel.frame, text=f"M{index} {label}")
    self._notebook.bind("<<NotebookTabChanged>>", self._on_tab)
    self._prev = 0

  @property
  def frame(self) -> ttk.Frame:
    """Root frame for the outer notebook."""
    return self._frame

  def on_leave(self) -> None:
    """Stop whichever motor panel is active."""
    for panel in self._panels:
      panel.on_leave()

  def _on_tab(self, _event=None) -> None:
    current = self._notebook.index(self._notebook.select())
    if 0 <= self._prev < len(self._panels):
      self._panels[self._prev].on_leave()
    self._prev = current
