"""pygame Xbox / gamepad reader for PC-side Yahboom piloting."""

from __future__ import annotations

import time

from yahboom_debug.xbox_pad_sample import XboxPadSample

try:
  import pygame
except ImportError as exc:  # pragma: no cover - host dependency
  pygame = None
  _PYGAME_ERROR = exc
else:
  _PYGAME_ERROR = None


class XboxPadReader:
  """Poll joystick 0 with auto-detected Xbox axis layout + rest centering."""

  def __init__(self, deadzone: float = 0.14) -> None:
    """``deadzone`` zeroes small stick noise after centering."""
    self._deadzone = deadzone
    self._joystick = None
    self._layout_name = ""
    # Axis indices into pygame get_axis().
    self._ax_lx = 0
    self._ax_ly = 1
    self._ax_rx = 2
    self._ax_ry = 3
    self._ax_lt = 4
    self._ax_rt = 5
    self._center_lx = 0.0
    self._center_ly = 0.0
    self._center_rx = 0.0
    self._center_ry = 0.0
    self._triggers_ok = True

  @property
  def layout_name(self) -> str:
    """Human-readable layout chosen at open()."""
    return self._layout_name

  def open(self) -> str:
    """Init pygame joystick, detect layout, capture rest centers."""
    if pygame is None:
      raise RuntimeError(
        f"pygame required: pip install pygame ({_PYGAME_ERROR})",
      )
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() < 1:
      raise RuntimeError("No joystick — plug an Xbox pad (USB or Bluetooth).")
    self._joystick = pygame.joystick.Joystick(0)
    self._joystick.init()
    # Let SDL settle before sampling rest pose (sticks released).
    for _ in range(8):
      pygame.event.pump()
      time.sleep(0.02)
    self._detect_layout()
    self._capture_centers()
    name = self._joystick.get_name()
    print(
      f"pad: {name} layout={self._layout_name} "
      f"RX=axis{self._ax_rx} LT=axis{self._ax_lt} "
      f"center_rx={self._center_rx:+.3f}",
      flush=True,
    )
    return name

  def close(self) -> None:
    """Release pygame."""
    if pygame is not None:
      pygame.quit()
    self._joystick = None

  def read(self) -> XboxPadSample:
    """Pump events and return a deadzoned, centered sample."""
    if self._joystick is None or pygame is None:
      raise RuntimeError("Joystick is not open.")
    pygame.event.pump()
    joy = self._joystick
    left_x = self._stick(joy, self._ax_lx, self._center_lx)
    left_y = self._stick(joy, self._ax_ly, self._center_ly)
    right_x = self._stick(joy, self._ax_rx, self._center_rx)
    right_y = self._stick(joy, self._ax_ry, self._center_ry)
    if self._triggers_ok:
      lt = self._trigger(self._raw(joy, self._ax_lt, -1.0))
      rt = self._trigger(self._raw(joy, self._ax_rt, -1.0))
    else:
      lt, rt = 0.0, 0.0
    hat_x, hat_y = 0, 0
    if joy.get_numhats() > 0:
      hat_x, hat_y = joy.get_hat(0)
    return XboxPadSample(
      left_x=left_x,
      left_y=left_y,
      right_x=right_x,
      right_y=right_y,
      lt=lt,
      rt=rt,
      hat_x=int(hat_x),
      hat_y=int(hat_y),
      button_a=joy.get_button(0) != 0 if joy.get_numbuttons() > 0 else False,
      name=joy.get_name(),
    )

  def _detect_layout(self) -> None:
    """Pick Windows Xbox (RX=2) vs alternate (RX=3) from rest values."""
    joy = self._joystick
    n = joy.get_numaxes()
    # Default: SDL2 / Xbox on Windows — LX LY RX RY LT RT
    self._ax_lx, self._ax_ly = 0, 1
    self._ax_rx, self._ax_ry = 2, 3
    self._ax_lt, self._ax_rt = 4, 5
    self._layout_name = "xbox-win RX=2 LT=4"
    self._triggers_ok = n >= 6
    if n < 4:
      self._layout_name = f"few-axes({n})"
      self._triggers_ok = False
      return
    # Heuristic: triggers rest near -1; stick axes rest near 0.
    a2 = self._raw(joy, 2, 0.0)
    a3 = self._raw(joy, 3, 0.0)
    a4 = self._raw(joy, 4, 0.0) if n > 4 else 0.0
    a5 = self._raw(joy, 5, 0.0) if n > 5 else 0.0
    # Alternate layout used previously by mistake: LT on 2/5, RX on 3.
    # If axis2 looks like a trigger (≈-1) and axis4 does not, prefer alt.
    if a2 < -0.7 and a5 < -0.7 and abs(a3) < 0.35:
      self._ax_rx, self._ax_ry = 3, 4
      self._ax_lt, self._ax_rt = 2, 5
      self._layout_name = "alt RX=3 LT=2"
      self._triggers_ok = True
    elif a4 < -0.7 and a5 < -0.7 and abs(a2) < 0.35:
      self._ax_rx, self._ax_ry = 2, 3
      self._ax_lt, self._ax_rt = 4, 5
      self._layout_name = "xbox-win RX=2 LT=4"
      self._triggers_ok = True
    else:
      # Fall back to RX=2; disable triggers if they don't look like triggers.
      self._ax_rx, self._ax_ry = 2, 3
      self._triggers_ok = a4 < -0.5 and a5 < -0.5
      self._layout_name = (
        "xbox-win RX=2 (no-trig)" if not self._triggers_ok else "xbox-win RX=2 LT=4"
      )

  def _capture_centers(self) -> None:
    """Remember stick rest pose so a biased RX does not yaw at idle."""
    joy = self._joystick
    self._center_lx = self._raw(joy, self._ax_lx, 0.0)
    self._center_ly = self._raw(joy, self._ax_ly, 0.0)
    self._center_rx = self._raw(joy, self._ax_rx, 0.0)
    self._center_ry = self._raw(joy, self._ax_ry, 0.0)

  def _raw(self, joy, index: int, default: float) -> float:
    if index < 0 or index >= joy.get_numaxes():
      return default
    return float(joy.get_axis(index))

  def _stick(self, joy, index: int, center: float) -> float:
    return self._dz(self._raw(joy, index, 0.0) - center)

  def _dz(self, value: float) -> float:
    if abs(value) < self._deadzone:
      return 0.0
    return max(-1.0, min(1.0, value))

  def _trigger(self, raw: float) -> float:
    # Map rest≈-1 .. pressed≈+1 → 0..1
    pressed = (raw + 1.0) * 0.5
    if pressed < self._deadzone:
      return 0.0
    return max(0.0, min(1.0, pressed))
