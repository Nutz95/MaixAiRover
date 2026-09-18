"""Main application: Xbox input, motion client, camera HUD."""

import threading

from maix import app, display, image, time, touchscreen

from lib.bluetooth_installer import BluetoothInstaller
from lib.camera_preview_service import CameraPreviewService
from lib.config_store import ConfigStore
from lib.motion_stack_factory import MotionStackFactory
from lib.touch_point import TouchPoint
from lib.ui_drawer import UiDrawer
from lib.xbox_input_service import XboxInputService


class XboxRoverApp:
  """Xbox teleop app driving the Hiwonder stack (stub or hardware I2C)."""

  TOUCH_DEBOUNCE_MS = 900
  SPEED_DEBOUNCE_MS = 160

  def __init__(self) -> None:
    self._config_store = ConfigStore()
    self._config = self._config_store.load()
    self._config_store.log_rover_settings()
    rover_cfg = self._config.get("rover", {})
    cam_cfg = self._config.get("camera", {})
    display_fps = max(1, min(30, int(cam_cfg.get("display_fps", 15))))
    self._display_interval_ms = max(1, int(1000 / display_fps))
    self._rover = MotionStackFactory().create(self._config)
    print(BluetoothInstaller().install())
    self._xbox = XboxInputService(self._config_store)
    self._disp = display.Display()
    self._ui = UiDrawer(self._disp.width(), self._disp.height())
    self._ts = touchscreen.TouchScreen()
    self._send_interval = rover_cfg.get("send_interval_ms", 30)
    self._exit = threading.Event()
    self._touch_action = None
    self._touch_lock = threading.Lock()
    self._touch_ignore_until = 0
    self._was_connected = False
    self._was_busy = False
    self._camera = None
    self._shutdown_done = False
    self._config_max_speed = int(rover_cfg.get("max_speed", 255))
    self._session_max_speed = self._config_max_speed
    self._speed_step = int(rover_cfg.get("speed_step", 5))
    self._last_speed_change_ms = 0
    self._rover.set_max_speed(self._session_max_speed)

  def run(self) -> None:
    """Start camera/display threads and run the input + motion control loop."""
    self._start_camera()

    display_thread = threading.Thread(target=self._display_loop, daemon=True)
    display_thread.start()

    send_ms = 0
    was_connected = False

    try:
      while not app.need_exit() and not self._exit.is_set():
        self._apply_rover_config()
        self._xbox.poll()
        self._handle_speed_bumpers()
        self._read_touch()
        self._handle_touch()
        self._on_connection_change()

        snap = self._xbox.snapshot()
        now = time.ticks_ms()
        if snap.connected and snap.drive is not None and now - send_ms >= self._send_interval:
          self._send_drive(snap.drive)
          send_ms = now
        elif was_connected and not snap.connected:
          self._rover.send_stop()

        was_connected = snap.connected
        time.sleep_ms(1)
    finally:
      self.shutdown()
      display_thread.join(timeout=1.0)

  def shutdown(self) -> None:
    """Stop input, motors, and camera once."""
    if self._shutdown_done:
      return
    self._shutdown_done = True
    self._exit.set()
    self._xbox.close()
    try:
      self._rover.send_stop()
    except Exception:
      pass
    if self._camera is not None:
      self._camera.stop()
      self._camera = None

  def _apply_rover_config(self) -> None:
    """Hot-reload rover tuning; reset session speed if file max_speed changes."""
    self._config_store.reload_if_changed()
    rover_cfg = self._config_store.rover_settings()
    file_max = int(rover_cfg.get("max_speed", 255))
    if file_max != self._config_max_speed:
      self._config_max_speed = file_max
      self._session_max_speed = file_max
    self._speed_step = int(rover_cfg.get("speed_step", 5))
    self._send_interval = rover_cfg.get("send_interval_ms", 30)
    self._rover.set_max_speed(self._session_max_speed)

  def _handle_speed_bumpers(self) -> None:
    """LB = slower, RB = faster (session max_speed shown in HUD)."""
    snap = self._xbox.snapshot()
    if not snap.connected:
      return
    edges = self._xbox.consume_speed_edges()
    if not edges.left_bumper and not edges.right_bumper:
      return
    now = time.ticks_ms()
    if now - self._last_speed_change_ms < self.SPEED_DEBOUNCE_MS:
      return
    changed = False
    if edges.left_bumper:
      self._session_max_speed = max(10, self._session_max_speed - self._speed_step)
      changed = True
    if edges.right_bumper:
      self._session_max_speed = min(255, self._session_max_speed + self._speed_step)
      changed = True
    if changed:
      self._last_speed_change_ms = now
      self._rover.set_max_speed(self._session_max_speed)
      print(
        f"speed: {int(self._session_max_speed * 100 / 255)}%"
        f" ({self._session_max_speed}/255)"
      )

  def _display_loop(self) -> None:
    last_draw = 0
    while not app.need_exit() and not self._exit.is_set():
      now = time.ticks_ms()
      if now - last_draw >= self._display_interval_ms:
        self._draw_frame()
        last_draw = now
      time.sleep_ms(4)

  def _start_camera(self) -> None:
    cam_cfg = self._config.get("camera", {})
    if not cam_cfg.get("enabled", True):
      return
    width = int(cam_cfg.get("width", 1280))
    height = int(cam_cfg.get("height", 720))
    fps = int(cam_cfg.get("fps", 60))
    pixel_format = cam_cfg.get("format", "rgb888")
    self._camera = CameraPreviewService(
      self._disp, width, height, fps=fps, pixel_format=pixel_format,
    )
    self._camera.start()
    if self._camera.error:
      print(f"camera disabled: {self._camera.error}")
      self._camera.stop()
      self._camera = None
    else:
      print(f"display: {int(1000 / self._display_interval_ms)} fps target")

  def _draw_frame(self) -> None:
    frame = None
    if self._camera is not None:
      frame = self._camera.get_frame()
    if frame is None:
      frame = image.Image(self._disp.width(), self._disp.height(), bg=image.COLOR_BLACK)

    snap = self._xbox.snapshot()
    self._ui.draw_overlay(
      frame,
      snap.connected,
      snap.busy,
      snap.state,
      snap.drive,
      self._session_max_speed,
      status=snap.status,
      progress=snap.progress,
    )
    self._disp.show(frame)

  def _read_touch(self) -> None:
    x, y, pressed = self._ts.read()
    if pressed:
      with self._touch_lock:
        self._touch_action = TouchPoint(x=x, y=y)

  def _on_connection_change(self) -> None:
    snap = self._xbox.snapshot()
    now = time.ticks_ms()
    if snap.connected != self._was_connected or snap.busy != self._was_busy:
      self._touch_ignore_until = now + self.TOUCH_DEBOUNCE_MS
      with self._touch_lock:
        self._touch_action = None
    self._was_connected = snap.connected
    self._was_busy = snap.busy

  def _handle_touch(self) -> None:
    if time.ticks_ms() < self._touch_ignore_until:
      return

    action = None
    with self._touch_lock:
      if self._touch_action is not None:
        action = self._touch_action
        self._touch_action = None
    if action is None:
      return

    snap = self._xbox.snapshot()
    if self._ui.back_rect().contains(action.x, action.y):
      self._xbox.request_stop()
      try:
        self._rover.send_stop()
      except OSError:
        pass
      self._exit.set()
      app.set_exit_flag(True)
      return

    if not snap.busy and not snap.connected:
      if self._ui.pair_rect().contains(action.x, action.y):
        self._xbox.start_pairing()
      elif self._ui.connect_rect().contains(action.x, action.y):
        self._xbox.start_connect()
      return

    if snap.connected and self._ui.disconnect_rect().contains(action.x, action.y):
      self._xbox.request_stop()
      try:
        self._rover.send_stop()
      except OSError:
        pass

  def _send_drive(self, drive) -> None:
    try:
      if drive.preset_action is not None:
        self._rover.send_preset(drive.preset_action)
        return
      if drive.is_idle():
        self._rover.send_stop()
        return
      self._rover.send_joystick(
        drive.axis_strafe,
        drive.axis_forward,
        drive.axis_spin,
        drive.axis_pivot,
      )
    except Exception as exc:
      print(f"drive: {exc}")
