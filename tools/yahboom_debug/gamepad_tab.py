"""Gamepad tab: live axes + closed-loop set_car_motion pilot."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from yahboom_debug.board_session import YahboomBoardSession
from yahboom_debug.xbox_pad_reader import XboxPadReader
from yahboom_debug.xbox_pad_sample import XboxPadSample


class GamepadTab:
  """Verify stick mapping against Yahboom chassis frame without MaixCAM."""

  def __init__(self, parent, session: YahboomBoardSession) -> None:
    """Build controls; piloting starts only when Arm is checked."""
    self._session = session
    self._reader = XboxPadReader()
    self._pad_name = ""
    self._frame = ttk.Frame(parent, padding=0)
    self._armed = tk.BooleanVar(value=False)
    self._invert_spin = tk.BooleanVar(value=False)
    self._status = tk.StringVar(value="Pad: not opened")
    self._layout_text = tk.StringVar(value="layout: —")
    self._axes_text = tk.StringVar(value="axes: —")
    self._cmd_text = tk.StringVar(value="cmd: vx=0 vy=0 vz=0")
    self._probe_text = tk.StringVar(value="probe: idle")
    self._max_vx = tk.DoubleVar(value=1.0)
    self._max_vy = tk.DoubleVar(value=1.0)
    self._max_vz = tk.DoubleVar(value=5.0)
    self._speed = tk.DoubleVar(value=1.0)
    self._build()

  @property
  def frame(self) -> ttk.Frame:
    """Root frame for notebook placement."""
    return self._frame

  def _build(self) -> None:
    canvas = tk.Canvas(self._frame, highlightthickness=0, bg="#1e1e2e")
    scroll = ttk.Scrollbar(self._frame, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    body = ttk.Frame(canvas, padding=8)
    window = canvas.create_window((0, 0), window=body, anchor="nw")

    def _on_body_configure(_event=None) -> None:
      canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event) -> None:
      canvas.itemconfigure(window, width=event.width)

    body.bind("<Configure>", _on_body_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event) -> None:
      # Windows / macOS
      delta = int(-event.delta / 120) if event.delta else 0
      if delta:
        canvas.yview_scroll(delta, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    top = ttk.Frame(body)
    top.pack(fill=tk.X)
    ttk.Button(top, text="Open pad", command=self.open_pad).pack(side=tk.LEFT)
    ttk.Button(top, text="Close pad", command=self.close_pad).pack(side=tk.LEFT, padx=4)
    ttk.Checkbutton(
      top, text="ARM teleop (set_car_motion)", variable=self._armed,
      command=self._on_arm,
    ).pack(side=tk.LEFT, padx=12)
    ttk.Checkbutton(
      top, text="Invert spin", variable=self._invert_spin,
    ).pack(side=tk.LEFT, padx=4)
    ttk.Label(top, textvariable=self._status).pack(side=tk.LEFT, padx=8)

    ttk.Label(body, textvariable=self._layout_text, foreground="#89b4fa").pack(
      anchor=tk.W, pady=(6, 0),
    )

    # Probe first — most used while diagnosing wiring.
    probe = ttk.LabelFrame(
      body,
      text="Chassis probe (disarms pad) — expected wheel pattern",
      padding=6,
    )
    probe.pack(fill=tk.X, pady=8)
    ttk.Label(
      probe,
      justify=tk.LEFT,
      text=(
        "vx+: all 4 forward | vy+ (crab LEFT): FL,RR back + FR,RL forward\n"
        "vz+ (CCW): left side back + right side forward. Needs M1=FL M2=RL M3=FR M4=RR."
      ),
    ).pack(anchor=tk.W)
    row = ttk.Frame(probe)
    row.pack(fill=tk.X, pady=4)
    ttk.Button(row, text="vx +0.3", command=lambda: self._probe(0.3, 0.0, 0.0)).pack(
      side=tk.LEFT, padx=2,
    )
    ttk.Button(row, text="vy +0.3 (crab)", command=lambda: self._probe(0.0, 0.3, 0.0)).pack(
      side=tk.LEFT, padx=2,
    )
    ttk.Button(row, text="vz +1.5 (spin)", command=lambda: self._probe(0.0, 0.0, 1.5)).pack(
      side=tk.LEFT, padx=2,
    )
    ttk.Button(row, text="STOP", command=self._safe_stop).pack(side=tk.LEFT, padx=8)
    ttk.Label(probe, textvariable=self._probe_text, font=("Consolas", 10)).pack(anchor=tk.W)

    lim = ttk.LabelFrame(body, text="Limits (match config yahboom.* × session)", padding=6)
    lim.pack(fill=tk.X, pady=8)
    self._add_scale(lim, "max_vx m/s", self._max_vx, 0.05, 1.5)
    self._add_scale(lim, "max_vy m/s", self._max_vy, 0.05, 1.5)
    self._add_scale(lim, "max_vz rad/s", self._max_vz, 0.2, 5.0)
    self._add_scale(lim, "speed %", self._speed, 0.1, 1.0)

    help_box = ttk.LabelFrame(body, text="Mapping Keyestudio / Maix", padding=6)
    help_box.pack(fill=tk.X)
    ttk.Label(
      help_box,
      justify=tk.LEFT,
      text=(
        "vx ← Left Y | vy crab ← LT/RT | vz ← Right X | pivot ← Left X | D-pad diagonals | A=STOP\n"
        "Gamepad only sends set_car_motion — it never remaps M1..M4."
      ),
    ).pack(anchor=tk.W)

    ttk.Label(body, textvariable=self._axes_text, font=("Consolas", 10)).pack(
      anchor=tk.W, pady=6,
    )
    ttk.Label(body, textvariable=self._cmd_text, font=("Consolas", 11)).pack(
      anchor=tk.W,
    )

  def _add_scale(self, parent, label: str, var: tk.DoubleVar, lo: float, hi: float) -> None:
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, pady=2)
    ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
    ttk.Scale(row, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL).pack(
      side=tk.LEFT, fill=tk.X, expand=True,
    )
    ttk.Label(row, textvariable=var, width=6).pack(side=tk.LEFT)

  def open_pad(self) -> None:
    """Open pygame joystick 0 (sticks released for center calib)."""
    try:
      self.close_pad()
      self._pad_name = self._reader.open()
      self._status.set(f"Pad: {self._pad_name}")
      self._layout_text.set(
        f"layout: {self._reader.layout_name}  "
        "(release sticks before Open pad)",
      )
    except Exception as open_error:
      self._status.set(f"Pad error: {open_error}")

  def close_pad(self) -> None:
    """Close pad and disarm."""
    self._armed.set(False)
    self._safe_stop()
    self._reader.close()
    self._status.set("Pad: closed")

  def on_leave(self) -> None:
    """Disarm when leaving the tab."""
    self._armed.set(False)
    self._safe_stop()

  def shutdown(self) -> None:
    """App close."""
    self.close_pad()

  def tick(self) -> None:
    """Poll pad and optionally stream chassis commands (~30 Hz from app)."""
    try:
      sample = self._reader.read()
    except RuntimeError:
      return
    except Exception as read_error:
      self._status.set(f"Pad error: {read_error}")
      return
    self._axes_text.set(
      f"LX={sample.left_x:+.2f} LY={sample.left_y:+.2f} "
      f"RX={sample.right_x:+.2f} RY={sample.right_y:+.2f} "
      f"LT={sample.lt:.2f} RT={sample.rt:.2f} "
      f"HAT=({sample.hat_x},{sample.hat_y}) A={int(sample.button_a)}"
    )
    vx, vy, vz = self._map_motion(sample)
    idle = abs(vx) < 1e-3 and abs(vy) < 1e-3 and abs(vz) < 1e-3
    self._cmd_text.set(
      f"cmd: vx={vx:+.3f} vy={vy:+.3f} vz={vz:+.3f}"
      + ("  [IDLE]" if idle else ""),
    )
    if sample.button_a:
      self._armed.set(False)
      self._safe_stop()
      return
    if not self._armed.get():
      return
    if not self._session.connected:
      self._status.set("Pad OK — connect board to drive")
      return
    try:
      # Always stream — including zeros when sticks idle — so yaw cannot stick.
      self._session.set_car_motion(vx, vy, vz)
    except Exception as drive_error:
      self._status.set(f"Drive error: {drive_error}")
      self._armed.set(False)

  def _map_motion(self, sample: XboxPadSample) -> tuple[float, float, float]:
    """Keyestudio-style mapping → Yahboom ``set_car_motion(vx,vy,vz)``.

    Crab = ``vy`` (triggers). Diagonal = ``vx+vy`` (D-pad). Drift = ``vx+vz``
    (left stick forward + right stick spin). Left X adds pivot yaw into ``vz``.
    """
    speed = max(0.0, min(1.0, float(self._speed.get())))
    max_vx = float(self._max_vx.get()) * speed
    max_vy = float(self._max_vy.get()) * speed
    max_vz = float(self._max_vz.get()) * speed

    # D-pad overrides sticks (same as Maix mapping.dpad).
    if sample.hat_x != 0 or sample.hat_y != 0:
      # pygame hat: y=-1 up, y=+1 down, x=-1 left, x=+1 right
      fwd = 0.0
      if sample.hat_y < 0:
        fwd = 1.0
      elif sample.hat_y > 0:
        fwd = -1.0
      # Rosmaster +vy = left, hat +x = right.
      return fwd * max_vx, -float(sample.hat_x) * max_vy, 0.0

    # Stick drive: left Y forward, triggers crab (RT = right = −vy), X = yaw.
    vx = (-sample.left_y) * max_vx
    vy = (sample.lt - sample.rt) * max_vy
    spin = sample.right_x
    if self._invert_spin.get():
      spin = -spin
    # Pivot (car-like yaw blend) shares vz with spin — Yahboom has no separate pivot API.
    pivot = sample.left_x
    vz = -(spin + pivot) * max_vz
    return vx, vy, vz

  def _on_arm(self) -> None:
    if not self._armed.get():
      self._safe_stop()

  def _probe(self, vx: float, vy: float, vz: float) -> None:
    """Send one pure axis so wiring can be judged without stick confusion."""
    self._armed.set(False)
    if not self._session.connected:
      self._probe_text.set("probe: board not connected")
      return
    try:
      self._session.set_car_motion(vx, vy, vz)
      self._cmd_text.set(f"cmd: vx={vx:+.3f} vy={vy:+.3f} vz={vz:+.3f}  [PROBE]")
      self._probe_text.set(
        f"probe: streaming vx={vx:+.2f} vy={vy:+.2f} vz={vz:+.2f} — press STOP when done",
      )
    except Exception as probe_error:
      self._probe_text.set(f"probe error: {probe_error}")

  def _safe_stop(self) -> None:
    self._probe_text.set("probe: idle")
    if not self._session.connected:
      return
    try:
      self._session.set_car_motion(0.0, 0.0, 0.0)
    except Exception as stop_error:
      print(f"gamepad: stop: {stop_error}")
