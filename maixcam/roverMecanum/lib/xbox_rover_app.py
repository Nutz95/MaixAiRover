"""Main application: Xbox input, motion client, camera HUD."""

from __future__ import annotations

import threading
from typing import Optional

from maix import app, display, time, touchscreen

from lib.app.drive_stack_loader import DriveStackLoader
from lib.app.teleop_tick_handler import TeleopTickHandler
from lib.ball_follow.ball_follow_runtime import BallFollowRuntime
from lib.camera.camera_config import CameraConfig
from lib.camera.camera_preview_service import CameraPreviewService
from lib.config.config_store import ConfigStore
from lib.config.motor_config import MotorConfig
from lib.config.rover_config import RoverConfig
from lib.esp.esp_link_config import EspLinkConfig
from lib.health.peripheral_health_checker import PeripheralHealthChecker
from lib.input.bluetooth_installer import BluetoothInstaller
from lib.input.drive_output import DriveOutput
from lib.input.teleop_control_thread import TeleopControlThread
from lib.input.xbox_input_service import XboxInputService
from lib.ui.checklist_panel import ChecklistPanel
from lib.ui.debug_panel import DebugPanel
from lib.ui.hud_composer import HudComposer
from lib.ui.hud_instruments import HudInstruments
from lib.ui.overlay_session import OverlaySession
from lib.ui.overlay_touch_router import OverlayTouchRouter
from lib.ui.touch_point import TouchPoint
from lib.ui.ui_drawer import UiDrawer
from lib.ui.yahboom_debug_panel import YahboomDebugPanel
from lib.yahboom.maix_battery_reader import MaixBatteryReader


class XboxRoverApp:
  """Thin composition root: wires services and runs the display loop."""

  TOUCH_DEBOUNCE_MS = 900

  def __init__(self) -> None:
    self._config_store = ConfigStore()
    self._config = self._config_store.load()
    self._config_store.log_rover_settings()
    rover_cfg = RoverConfig.from_mapping(self._config.get("rover", {}))
    cam_cfg = CameraConfig.from_mapping(self._config.get("camera", {}))
    motor_cfg = MotorConfig.from_mapping(self._config.get("motors", {}))
    esp_links = EspLinkConfig.from_mapping(self._config.get("esp", {}))
    self._motor_limit = motor_cfg.max_setpoint
    self._display_interval_ms = max(1, int(1000 / cam_cfg.display_fps))
    self._disp = display.Display()
    self._ui = UiDrawer(self._disp.width(), self._disp.height())
    self._checklist_panel = ChecklistPanel(self._disp.width(), self._disp.height())
    self._debug_panel = DebugPanel(self._disp.width(), self._disp.height())
    self._yahboom_debug_panel = YahboomDebugPanel(
      self._disp.width(), self._disp.height(),
    )
    stack = DriveStackLoader().load(self._config, esp_links)
    self._drive_backend = stack.kind
    self._rover = stack.rover
    self._yahboom_board = stack.yahboom_board
    self._yahboom_debug = stack.yahboom_debug
    self._debug = stack.esp_front_debug
    self._rear_debug = stack.esp_rear_debug
    self._maix_battery = MaixBatteryReader()
    print(BluetoothInstaller().install())
    self._xbox = XboxInputService(self._config_store)
    self._ts = touchscreen.TouchScreen()
    self._exit = threading.Event()
    self._touch_action: Optional[TouchPoint] = None
    self._touch_lock = threading.Lock()
    self._touch_ignore_until = 0
    self._touch_was_pressed = False
    self._was_connected = False
    self._was_busy = False
    self._camera: Optional[CameraPreviewService] = None
    self._shutdown_done = False
    self._rover.set_max_speed(rover_cfg.max_speed)
    self._ball = BallFollowRuntime(
      self._config,
      self._rover,
      motor_cfg,
      yahboom_board=self._yahboom_board,
      get_frame=self._ball_frame,
    )
    self._checklist = None
    self._checklist_open = False
    self._checklist_lock = threading.Lock()
    self._health = PeripheralHealthChecker(
      esp_wifi_host=esp_links.front.wifi_host,
      esp_wifi_port=esp_links.front.wifi_port,
      esp_uart_port=esp_links.front.uart_port,
      rear_uart_port=(esp_links.rear.uart_port if esp_links.rear else ""),
      drive_backend=self._drive_backend,
    )
    self._cam_cfg = cam_cfg
    self._display_fps = cam_cfg.display_fps
    self._control = TeleopControlThread(
      xbox=self._xbox,
      rover=self._rover,
      send_drive=self._send_drive,
      send_interval_ms=rover_cfg.send_interval_ms,
      on_tick=self._control_tick,
    )
    self._tick = TeleopTickHandler(
      config_store=self._config_store,
      xbox=self._xbox,
      rover=self._rover,
      ball=self._ball,
      control=self._control,
      maix_battery=self._maix_battery,
      yahboom_board=self._yahboom_board,
      esp_debug=self._debug,
      session_max_speed=rover_cfg.max_speed,
      config_max_speed=rover_cfg.max_speed,
      speed_step=rover_cfg.speed_step,
      send_interval_ms=rover_cfg.send_interval_ms,
    )
    self._touch_router = OverlayTouchRouter(self)
    self._overlays = OverlaySession(self)
    self._hud = HudComposer(self)

  def run(self) -> None:
    """Teleop in background; main thread draws HUD (Maix display API)."""
    self._start_camera()
    self._control.start()
    loop_sleep_ms = max(1, min(8, self._display_interval_ms // 2))
    last_draw = 0
    try:
      while not app.need_exit() and not self._exit.is_set():
        self._read_touch()
        self._handle_touch()
        self._overlays.on_connection_change()
        now = time.ticks_ms()
        if now - last_draw >= self._display_interval_ms:
          self._hud.draw()
          last_draw = time.ticks_ms()
        else:
          time.sleep_ms(loop_sleep_ms)
    finally:
      self.shutdown()

  def shutdown(self) -> None:
    """Stop motors, teleop, USB, camera, then Xbox (avoids teardown races)."""
    if self._shutdown_done:
      return
    self._shutdown_done = True
    self._exit.set()
    try:
      self._ball.disable()
    except Exception as ball_error:
      print(f"shutdown: ball_follow: {ball_error}")
    try:
      self._rover.send_stop()
    except Exception as stop_error:
      print(f"shutdown: send_stop: {stop_error}")
    self._control.stop()
    if self._debug is not None:
      try:
        self._debug.shutdown()
      except Exception as debug_error:
        print(f"shutdown: esp debug: {debug_error}")
    if self._rear_debug is not None:
      try:
        self._rear_debug.shutdown()
      except Exception as debug_error:
        print(f"shutdown: rear esp debug: {debug_error}")
    if self._yahboom_board is not None:
      try:
        self._yahboom_board.close()
      except Exception as board_error:
        print(f"shutdown: yahboom: {board_error}")
    if self._camera is not None:
      try:
        self._camera.stop()
      except Exception as camera_error:
        print(f"shutdown: camera: {camera_error}")
      self._camera = None
    try:
      self._xbox.close()
    except Exception as xbox_error:
      print(f"shutdown: xbox: {xbox_error}")

  def _control_tick(self) -> None:
    """Delegate lightly to the typed teleop tick handler."""
    self._tick.tick()

  def _ball_frame(self):
    """Latest camera frame for ball detection (may be None)."""
    if self._camera is None:
      return None
    return self._camera.get_frame()

  def _start_camera(self) -> None:
    cam_cfg = self._cam_cfg
    if not cam_cfg.enabled:
      print("camera: disabled (teleop black HUD — enable for YOLO mode)")
      return
    fps = cam_cfg.fps or self._display_fps
    self._camera = CameraPreviewService(
      self._disp,
      cam_cfg.width,
      cam_cfg.height,
      fps=fps,
      pixel_format=cam_cfg.format,
    )
    self._camera.start()
    if self._camera.error:
      print(f"camera disabled: {self._camera.error}")
      self._camera.stop()
      self._camera = None
    else:
      print(f"display: {self._display_fps} fps target")

  def _hud_instruments(self) -> HudInstruments:
    """Cached instruments filled by the teleop thread (no USB on draw path)."""
    return self._tick.hud_instruments()

  @property
  def _session_max_speed(self) -> int:
    """Session max speed for HUD (owned by TeleopTickHandler)."""
    return self._tick.session_max_speed

  def _read_touch(self) -> None:
    """Latch one press edge — holding a finger must not re-fire after a modal closes."""
    x, y, pressed = self._ts.read()
    if pressed and not self._touch_was_pressed:
      with self._touch_lock:
        self._touch_action = TouchPoint(x=x, y=y)
    self._touch_was_pressed = bool(pressed)

  def _arm_touch_ignore(self) -> None:
    """Ignore touch until release + debounce (after closing overlays)."""
    self._touch_ignore_until = time.ticks_ms() + self.TOUCH_DEBOUNCE_MS
    self._touch_was_pressed = True
    with self._touch_lock:
      self._touch_action = None

  def _request_exit(self) -> None:
    self._xbox.request_stop()
    try:
      self._rover.send_stop()
    except OSError as stop_error:
      print(f"exit: send_stop: {stop_error}")
    self._exit.set()
    app.set_exit_flag(True)

  def _handle_touch(self) -> None:
    if time.ticks_ms() < self._touch_ignore_until:
      return
    action: Optional[TouchPoint] = None
    with self._touch_lock:
      if self._touch_action is not None:
        action = self._touch_action
        self._touch_action = None
    if action is None:
      return
    self._touch_router.handle(action)

  def _send_drive(self, drive: DriveOutput) -> None:
    with self._checklist_lock:
      if self._checklist_open:
        return
    if self._debug is not None and self._debug.is_open():
      return
    if self._yahboom_debug is not None and self._yahboom_debug.is_open():
      return
    try:
      self._ball.dispatch(drive)
    except Exception as exc:
      print(f"drive: {type(exc).__name__}: {exc}")
