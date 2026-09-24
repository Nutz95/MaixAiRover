import os
import select
import struct

from lib.input.controller_state import ControllerState
from lib.input.controller_button import ControllerButton
from lib.input.evdev_axis_mapper import EvdevAxisMapper
from lib.input.evdev_trigger_mapper import EvdevTriggerMapper
from lib.input.evdev_constants import (
  ABS_HAT0X, ABS_HAT0Y, AXIS_MAX, BTN_A, BTN_B, BTN_DPAD_DOWN, BTN_DPAD_LEFT, BTN_DPAD_RIGHT,
  BTN_DPAD_UP, BTN_SELECT, BTN_START, BTN_THUMBL, BTN_THUMBR, BTN_TL, BTN_TL2,
  BTN_TR, BTN_TR2, BTN_X, BTN_Y, EV_ABS, EV_KEY, EV_SYN, SYN_REPORT,
  default_abs_range,
)
from lib.input.evdev_ioctl import read_absinfo
from lib.input.evdev_sysfs_reader import EvdevSysfsReader
from lib.input.evdev_xbox_layout import XboxAxisLayout

_BTN_BY_CODE = {
  BTN_A: ControllerButton.A,
  BTN_B: ControllerButton.B,
  BTN_X: ControllerButton.X,
  BTN_Y: ControllerButton.Y,
  BTN_TL: ControllerButton.LB,
  BTN_TR: ControllerButton.RB,
  BTN_THUMBL: ControllerButton.LB,
  BTN_THUMBR: ControllerButton.RB,
  BTN_TL2: ControllerButton.LT,
  BTN_TR2: ControllerButton.RT,
  BTN_SELECT: ControllerButton.SELECT,
  BTN_START: ControllerButton.START,
}


class EvdevReader:
  """Read Xbox evdev events (input thread only)."""

  def __init__(self, event_path, config=None):
    self.event_path = event_path
    self._config = config or {}
    self.state = ControllerState()
    self._sysfs = EvdevSysfsReader()
    evdev_cfg = self._config.get("evdev", {})
    self._layout = XboxAxisLayout.detect(self._sysfs, event_path, evdev_cfg)
    self._ev_struct, self._ev_size = self._detect_event_size(event_path)
    self._mappers = {}
    self._observed = {}
    self._file = None
    self.event_count = 0
    self.kernel_state_available = False
    self._lt_btn = 0
    self._rt_btn = 0
    self._dpad_x = 0
    self._dpad_y = 0
    self._dpad_btn_x = 0
    self._dpad_btn_y = 0

  def open(self):
    """Open evdev unbuffered/non-blocking. Buffered ``open()`` blocks on 8K reads."""
    fd = os.open(self.event_path, os.O_RDONLY | os.O_NONBLOCK)
    self._file = os.fdopen(fd, "rb", buffering=0)
    self._init_mappers()

  def _init_mappers(self):
    """Create axis mappers up front so kernel sync always has a target."""
    layout = self._layout
    trigger_codes = {layout.lt, layout.rt}
    for code in (layout.left_x, layout.left_y, layout.right_x, layout.right_y, layout.lt, layout.rt):
      prefer_trigger = code in trigger_codes
      info = read_absinfo(self._file, code)
      if info is not None:
        self.kernel_state_available = True
        self._ensure_mapper_with_range(
          code, info.value, info.minimum, info.maximum, info.flat, prefer_trigger,
        )
        continue
      axis_range = self._axis_range(code, prefer_trigger)
      raw = axis_range.minimum if prefer_trigger else (axis_range.minimum + axis_range.maximum) // 2
      self._ensure_mapper_with_range(
        code, raw, axis_range.minimum, axis_range.maximum, axis_range.flat, prefer_trigger,
      )

  def close(self):
    """Close the evdev file descriptor."""
    if self._file is not None:
      try:
        self._file.close()
      except OSError as close_error:
        print(f'evdev: close: {close_error}')
      self._file = None

  def drain_available(self):
    """Read every pending evdev event (non-blocking)."""
    return self._drain_events()

  def poll_inputs(self):
    """
    One input frame: events for buttons, then kernel ABS truth for sticks.

    Axes are read via EVIOCGABS every poll so missed evdev packets cannot
    leave sticks stuck at the last value.
    """
    if self._file is None:
      return
    self.drain_available()
    self.sync_axes_from_kernel()

  def sync_axes_from_kernel(self):
    """Force stick/trigger state from kernel (ioctl, then sysfs fallback)."""
    layout = self._layout
    trigger_codes = {layout.lt, layout.rt}
    for code in (layout.left_x, layout.left_y, layout.right_x, layout.right_y, layout.lt, layout.rt):
      info = read_absinfo(self._file, code)
      if info is not None:
        self.kernel_state_available = True
        self._ensure_mapper_with_range(
          code, info.value, info.minimum, info.maximum, info.flat, code in trigger_codes,
        )
        continue
      val = self._sysfs.read_abs_value(self.event_path, code)
      if val is not None:
        self.kernel_state_available = True
        self._feed_abs(code, val)
    self._sync_axes()

  def _ensure_mapper_with_range(self, code, raw, min_v, max_v, flat, prefer_trigger):
    """Create or refresh a mapper when kernel absinfo arrives."""
    if prefer_trigger and max_v - min_v > 1024:
      prefer_trigger = False
    mapper = self._mappers.get(code)
    needs_rebuild = (
      mapper is None
      or mapper.min_v != min_v
      or mapper.max_v != max_v
      or mapper.flat != flat
      or isinstance(mapper, EvdevTriggerMapper) != prefer_trigger
    )
    if needs_rebuild:
      mapper = (
        EvdevTriggerMapper(min_v, max_v, flat)
        if prefer_trigger
        else EvdevAxisMapper(min_v, max_v, flat)
      )
      self._mappers[code] = mapper
    mapper.set_raw(raw)

  def _drain_events(self):
    if self._file is None:
      return 0
    count = 0
    while self._file is not None:
      ready, _, _ = select.select([self._file], [], [], 0)
      if not ready:
        break
      try:
        data = os.read(self._file.fileno(), self._ev_size)
      except BlockingIOError:
        break
      except OSError as exc:
        if exc.errno in (11, 19):  # EAGAIN/ENODEV
          if exc.errno == 19:
            raise
          break
        raise
      if not data or len(data) < self._ev_size:
        break
      self._process_event(data)
      count += 1
    return count

  def _process_event(self, data):
    _sec, _usec, ev_type, code, value = self._ev_struct.unpack(data)
    self.event_count += 1
    if ev_type == EV_ABS:
      self._feed_abs(code, value)
    elif ev_type == EV_KEY:
      self._feed_key(code, value)
    elif ev_type == EV_SYN and code == SYN_REPORT:
      return

  def _axis_range(self, code, prefer_trigger=False):
    info = self._sysfs.read_absinfo_real(self.event_path, code)
    if info is not None:
      return info
    return default_abs_range(code, prefer_trigger=prefer_trigger)

  def _create_mapper(self, code, prefer_trigger):
    axis_range = self._axis_range(code, prefer_trigger)
    min_v, max_v, flat = axis_range.minimum, axis_range.maximum, axis_range.flat
    if prefer_trigger and max_v - min_v > 1024:
      prefer_trigger = False
    if prefer_trigger:
      return EvdevTriggerMapper(min_v, max_v, flat)
    return EvdevAxisMapper(min_v, max_v, flat)

  def _ensure_mapper(self, code, value):
    obs = self._observed.get(code)
    if obs is None:
      obs = {"min": value, "max": value}
      self._observed[code] = obs
    else:
      obs["min"] = min(obs["min"], value)
      obs["max"] = max(obs["max"], value)

    mapper = self._mappers.get(code)
    if mapper is not None:
      return mapper

    trigger_codes = {self._layout.lt, self._layout.rt}
    prefer_trigger = code in trigger_codes
    span = obs["max"] - obs["min"]
    if prefer_trigger and span > 1024:
      prefer_trigger = False
    if not prefer_trigger and span <= 1024 and obs["min"] >= 0 and code in trigger_codes:
      prefer_trigger = True

    mapper = self._create_mapper(code, prefer_trigger)
    self._mappers[code] = mapper
    return mapper

  def _feed_abs(self, code, value):
    if code in (ABS_HAT0X, 6):
      self._dpad_x = self._hat_value(value)
      return
    if code in (ABS_HAT0Y, 7):
      self._dpad_y = self._hat_value(value)
      return
    mapper = self._ensure_mapper(code, value)
    mapper.set_raw(value)

  @staticmethod
  def _hat_value(value):
    if value > 0:
      return 1
    if value < 0:
      return -1
    return 0

  def _feed_key(self, code, value):
    pressed = value != 0
    if code in (BTN_TL, BTN_THUMBL):
      self.state.set_button(ControllerButton.LB, pressed)
      return
    if code in (BTN_TR, BTN_THUMBR):
      self.state.set_button(ControllerButton.RB, pressed)
      return
    if code == BTN_TL2:
      self._lt_btn = AXIS_MAX if pressed else 0
      return
    if code == BTN_TR2:
      self._rt_btn = AXIS_MAX if pressed else 0
      return
    if code == BTN_DPAD_LEFT:
      self._dpad_btn_x = -1 if value else 0
      return
    if code == BTN_DPAD_RIGHT:
      self._dpad_btn_x = 1 if value else 0
      return
    if code == BTN_DPAD_UP:
      self._dpad_btn_y = -1 if value else 0
      return
    if code == BTN_DPAD_DOWN:
      self._dpad_btn_y = 1 if value else 0
      return
    button = _BTN_BY_CODE.get(code)
    if button is None:
      return
    self.state.set_button(button, value != 0)

  def _sync_axes(self):
    layout = self._layout
    self.state.left_x = self._read_axis(layout.left_x)
    self.state.left_y = self._read_axis(layout.left_y)
    self.state.right_x = self._read_axis(layout.right_x)
    self.state.right_y = self._read_axis(layout.right_y)
    self.state.lt = max(self._read_axis(layout.lt), self._lt_btn)
    self.state.rt = max(self._read_axis(layout.rt), self._rt_btn)
    hat_x = self._dpad_x if self._dpad_x != 0 else self._dpad_btn_x
    hat_y = self._dpad_y if self._dpad_y != 0 else self._dpad_btn_y
    self.state.dpad_x = hat_x
    self.state.dpad_y = hat_y

  def _read_axis(self, code):
    mapper = self._mappers.get(code)
    if mapper is None:
      return 0
    return mapper.to_axis()

  def _detect_event_size(self, event_path):
    # ponytail: 64-bit input_event is 24 bytes; skip probing (it ate HID reports).
    if struct.calcsize("L") == 8:
      return struct.Struct("QQHHi"), 24
    return struct.Struct("llHHi"), 16
