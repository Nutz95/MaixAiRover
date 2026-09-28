"""Single-motor open-loop PWM panel (one Yahboom channel)."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from yahboom_debug.board_session import YahboomBoardSession


class MotorPanel:
  """Unit test one motor: fwd / rev / stop + encoder delta."""

  def __init__(
    self,
    parent,
    session: YahboomBoardSession,
    index: int,
    label: str,
  ) -> None:
    """``index`` is 1..4 (M1..M4)."""
    self._session = session
    self._index = index
    self._label = label
    self._frame = ttk.Frame(parent, padding=8)
    self._pwm = tk.IntVar(value=30)
    self._seconds = tk.DoubleVar(value=1.5)
    self._status = tk.StringVar(value="idle")
    self._enc_text = tk.StringVar(value="enc: —")
    self._build()

  @property
  def frame(self) -> ttk.Frame:
    """Panel root for a notebook tab."""
    return self._frame

  def _build(self) -> None:
    ttk.Label(
      self._frame,
      text=f"Motor M{self._index} = {self._label}  (open-loop set_motor)",
      font=("Segoe UI", 11, "bold"),
    ).pack(anchor=tk.W)
    ttk.Label(
      self._frame,
      text="Wheels OFF the ground. DC 6–13 V ON. Only this channel is driven.",
    ).pack(anchor=tk.W, pady=4)

    row = ttk.Frame(self._frame)
    row.pack(fill=tk.X, pady=6)
    ttk.Label(row, text="PWM").pack(side=tk.LEFT)
    ttk.Scale(row, from_=5, to=100, variable=self._pwm, orient=tk.HORIZONTAL).pack(
      side=tk.LEFT, fill=tk.X, expand=True, padx=6,
    )
    ttk.Label(row, textvariable=self._pwm, width=4).pack(side=tk.LEFT)

    row2 = ttk.Frame(self._frame)
    row2.pack(fill=tk.X, pady=4)
    ttk.Label(row2, text="Duration s").pack(side=tk.LEFT)
    ttk.Scale(row2, from_=0.3, to=5.0, variable=self._seconds, orient=tk.HORIZONTAL).pack(
      side=tk.LEFT, fill=tk.X, expand=True, padx=6,
    )

    btns = ttk.Frame(self._frame)
    btns.pack(fill=tk.X, pady=8)
    ttk.Button(btns, text="FWD", command=lambda: self._pulse(1)).pack(side=tk.LEFT)
    ttk.Button(btns, text="REV", command=lambda: self._pulse(-1)).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="STOP", command=self._stop).pack(side=tk.LEFT)
    ttk.Button(btns, text="Read encoders", command=self._read_enc).pack(side=tk.LEFT, padx=12)

    ttk.Label(self._frame, textvariable=self._status).pack(anchor=tk.W, pady=4)
    ttk.Label(self._frame, textvariable=self._enc_text, font=("Consolas", 10)).pack(
      anchor=tk.W,
    )
    ttk.Label(
      self._frame,
      justify=tk.LEFT,
      text=(
        "Expect: FWD increases this motor's encoder when wiring matches silk.\n"
        "Map: M1=FL  M2=RL  M3=FR  M4=RR\n"
        "If the wrong wheel moves → swap motor connectors on the board."
      ),
    ).pack(anchor=tk.W, pady=8)

  def on_leave(self) -> None:
    """Stop when leaving this motor sub-tab."""
    self._stop()

  def _pulse(self, sign: int) -> None:
    if not self._session.connected:
      self._status.set("Connect the board first")
      return
    try:
      volts = self._session.battery_v()
    except Exception as bat_error:
      self._status.set(f"battery read failed: {bat_error}")
      return
    if volts < 6.0:
      self._status.set(f"ABORT battery={volts:.1f} V — need DC IN + switch ON")
      return
    duty = max(1, min(100, int(self._pwm.get()))) * sign
    seconds = max(0.1, float(self._seconds.get()))
    try:
      before = self._session.encoders()
      self._session.set_motor_pwm(self._index, duty)
      self._status.set(
        f"M{self._index} ({self._label}) PWM={duty} for {seconds:.1f}s "
        f"(bat={volts:.1f} V)",
      )
      self._frame.after(int(seconds * 1000), lambda b=before: self._finish(b))
    except Exception as run_error:
      self._status.set(f"error: {run_error}")
      self._stop()

  def _finish(self, before: tuple[int, int, int, int]) -> None:
    try:
      self._session.set_motor_pwm(self._index, 0)
      time.sleep(0.15)
      after = self._session.encoders()
      delta = after[self._index - 1] - before[self._index - 1]
      self._enc_text.set(
        f"enc now={after}  delta M{self._index}={delta}"
      )
      if delta == 0:
        self._status.set("stopped — encoder delta 0 (wiring / power?)")
      else:
        self._status.set(f"stopped — encoder moved Δ={delta}")
    except Exception as finish_error:
      self._status.set(f"finish error: {finish_error}")

  def _stop(self) -> None:
    if not self._session.connected:
      return
    try:
      self._session.set_motor_pwm(self._index, 0)
      self._status.set("STOP")
    except Exception as stop_error:
      self._status.set(f"stop error: {stop_error}")

  def _read_enc(self) -> None:
    if not self._session.connected:
      self._enc_text.set("enc: not connected")
      return
    try:
      enc = self._session.encoders()
      self._enc_text.set(f"enc M1..M4={enc}")
    except Exception as enc_error:
      self._enc_text.set(f"enc error: {enc_error}")
