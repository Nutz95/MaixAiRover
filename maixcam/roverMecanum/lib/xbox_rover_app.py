"""Main application: Xbox input, motion client, camera HUD."""

import threading

from maix import app, display, image, time, touchscreen

from lib.bluetooth_installer import BluetoothInstaller
from lib.camera_config import CameraConfig
from lib.camera_preview_service import CameraPreviewService
from lib.checklist_panel import ChecklistPanel
from lib.config_store import ConfigStore
from lib.debug_panel import DebugPanel
from lib.drive_backend_config import DriveBackendConfig
from lib.drive_backend_kind import DriveBackendKind
from lib.esp_debug_action import EspDebugAction
from lib.esp_debug_session import EspDebugSession
from lib.esp_link_config import EspLinkConfig
from lib.hud_instruments import from_telem, from_yahboom_imu
from lib.motion_stack_factory import MotionStackFactory
from lib.motor_config import MotorConfig
from lib.peripheral_health_checker import PeripheralHealthChecker
from lib.rover_config import RoverConfig
from lib.teleop_control_thread import TeleopControlThread
from lib.touch_point import TouchPoint
from lib.ui_drawer import UiDrawer
from lib.xbox_input_service import XboxInputService


class XboxRoverApp:
  """Xbox teleop app with HUD, checklist, and ESP debug panel."""

  TOUCH_DEBOUNCE_MS = 900
  SPEED_DEBOUNCE_MS = 160

  def __init__(self) -> None:
    self._config_store = ConfigStore()
    self._config = self._config_store.load()
    self._config_store.log_rover_settings()
    rover_cfg = RoverConfig.from_mapping(self._config.get("rover", {}))
    cam_cfg = CameraConfig.from_mapping(self._config.get("camera", {}))
    motor_cfg = MotorConfig.from_mapping(self._config.get("motors", {}))
    esp_links = EspLinkConfig.from_mapping(self._config.get("esp", {}))
    backend = DriveBackendConfig.from_root(self._config)
    self._drive_backend = backend.kind
    self._motor_limit = motor_cfg.max_setpoint
    display_fps = cam_cfg.display_fps
    self._display_interval_ms = max(1, int(1000 / display_fps))
    self._disp = display.Display()
    self._ui = UiDrawer(self._disp.width(), self._disp.height())
    self._checklist_panel = ChecklistPanel(self._disp.width(), self._disp.height())
    self._debug_panel = DebugPanel(self._disp.width(), self._disp.height())
    self._esp_links = esp_links
    self._debug = None
    self._rear_debug = None
    self._yahboom_board = None
    if self._drive_backend is DriveBackendKind.YAHBOOM:
      bundle = MotionStackFactory().create_yahboom(self._config)
      self._rover = bundle.client
      self._yahboom_board = bundle.yahboom_board
      print("drive_backend: yahboom (USB Rosmaster closed-loop)")
    else:
      self._debug = EspDebugSession(uart_port=esp_links.front.uart_port)
      set_rear = None
      if esp_links.rear is not None:
        self._rear_debug = EspDebugSession(uart_port=esp_links.rear.uart_port)
        set_rear = self._rear_debug.set_drive
      bundle = MotionStackFactory().create_esp(
        self._config,
        set_front_drive=self._debug.set_drive,
        set_rear_drive=set_rear,
      )
      self._rover = bundle.client
      print("drive_backend: esp (Waveshare UART)")
    print(BluetoothInstaller().install())
    self._xbox = XboxInputService(self._config_store)
    self._ts = touchscreen.TouchScreen()
    self._send_interval = rover_cfg.send_interval_ms
    self._exit = threading.Event()
    self._touch_action = None
    self._touch_lock = threading.Lock()
    self._touch_ignore_until = 0
    self._touch_was_pressed = False
    self._was_connected = False
    self._was_busy = False
    self._camera = None
    self._shutdown_done = False
    self._config_max_speed = rover_cfg.max_speed
    self._session_max_speed = self._config_max_speed
    self._speed_step = rover_cfg.speed_step
    self._last_speed_change_ms = 0
    self._rover.set_max_speed(self._session_max_speed)
    self._checklist = None
    self._checklist_open = False
    self._checklist_lock = threading.Lock()
    self._health = PeripheralHealthChecker(
      esp_wifi_host=esp_links.front.wifi_host,
      esp_wifi_port=esp_links.front.wifi_port,
      esp_uart_port=esp_links.front.uart_port,
      rear_uart_port=(esp_links.rear.uart_port if esp_links.rear else ""),
    )
    self._cam_cfg = cam_cfg
    self._display_fps = display_fps
    self._control = TeleopControlThread(
      xbox=self._xbox,
      rover=self._rover,
      send_drive=self._send_drive,
      send_interval_ms=rover_cfg.send_interval_ms,
      on_tick=self._control_tick,
    )

  def run(self) -> None:
    """Start HUD + control threads; main thread only handles touch/UI."""
    self._start_camera()
    display_thread = threading.Thread(
      target=self._display_loop, daemon=True, name="hud-display",
    )
    display_thread.start()
    self._control.start()
    try:
      while not app.need_exit() and not self._exit.is_set():
        self._read_touch()
        self._handle_touch()
        self._on_connection_change()
        time.sleep_ms(8)
    finally:
      self.shutdown()
      display_thread.join(timeout=1.0)

  def shutdown(self) -> None:
    """Stop input, motors, and camera once."""
    if self._shutdown_done:
      return
    self._shutdown_done = True
    self._exit.set()
    self._control.stop()
    if self._debug is not None:
      self._debug.shutdown()
    if self._rear_debug is not None:
      self._rear_debug.shutdown()
    if self._yahboom_board is not None:
      try:
        self._yahboom_board.close()
      except Exception:
        pass
    self._xbox.close()
    try:
      self._rover.send_stop()
    except Exception:
      pass
    if self._camera is not None:
      self._camera.stop()
      self._camera = None

  def _control_tick(self) -> None:
    """Light work on the control thread (config reload + LB/RB speed)."""
    self._apply_rover_config()
    self._handle_speed_bumpers()
    self._control.set_send_interval_ms(self._send_interval)

  def _apply_rover_config(self) -> None:
    """Hot-reload rover tuning; reset session speed if file max_speed changes."""
    self._config_store.reload_if_changed()
    rover_cfg = self._config_store.rover_settings()
    if rover_cfg.max_speed != self._config_max_speed:
      self._config_max_speed = rover_cfg.max_speed
      self._session_max_speed = rover_cfg.max_speed
    self._speed_step = rover_cfg.speed_step
    self._send_interval = rover_cfg.send_interval_ms
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
      wait = self._display_interval_ms - (now - last_draw)
      if wait > 1:
        time.sleep_ms(wait)
        continue
      self._draw_frame()
      last_draw = time.ticks_ms()

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

  def _draw_frame(self) -> None:
    with self._checklist_lock:
      checklist_open = self._checklist_open
      checklist = self._checklist
    debug_open = False
    debug_link = ""
    debug_status = ""
    debug_telem = None
    if self._debug is not None:
      snap_dbg = self._debug.snapshot()
      debug_open = snap_dbg.panel_open
      debug_link = snap_dbg.link_name
      debug_status = snap_dbg.status
      debug_telem = snap_dbg.telem

    if checklist_open:
      frame = image.Image(self._disp.width(), self._disp.height(), bg=image.COLOR_BLACK)
      self._checklist_panel.draw(frame, checklist)
      self._disp.show(frame)
      return

    if debug_open:
      frame = image.Image(self._disp.width(), self._disp.height(), bg=image.COLOR_BLACK)
      self._debug_panel.draw(
        frame, link_name=debug_link, status=debug_status, telem=debug_telem,
      )
      self._disp.show(frame)
      return

    frame = None
    if self._camera is not None:
      frame = self._camera.get_frame()
    if frame is None:
      frame = image.Image(self._disp.width(), self._disp.height(), bg=image.COLOR_BLACK)
    else:
      # MaixPy draw_* rejects YUV (config default yuv420); HUD needs RGB.
      frame = self._drawable_rgb(frame)
    snap = self._xbox.snapshot()
    wheels = self._rover.last_wheel_speeds()
    self._ui.draw_overlay(
      frame,
      snap.connected,
      snap.busy,
      snap.state,
      snap.drive,
      self._session_max_speed,
      status=snap.status,
      progress=snap.progress,
      instruments=self._hud_instruments(),
      wheel_fl=wheels.front_left,
      wheel_fr=wheels.front_right,
      motor_limit=self._motor_limit,
    )
    self._disp.show(frame)

  def _hud_instruments(self):
    """HUD instruments from ESP TELEM or Yahboom IMU."""
    if self._yahboom_board is not None:
      return from_yahboom_imu(self._yahboom_board.imu_attitude())
    if self._debug is not None:
      return from_telem(self._debug.telem())
    return from_telem(None)

  @staticmethod
  def _drawable_rgb(frame):
    """Return an RGB888 image MaixPy can draw on."""
    try:
      fmt = frame.format()
    except Exception:
      return frame
    if fmt in (image.Format.FMT_RGB888, image.Format.FMT_BGR888):
      return frame
    # MaixCAM2: YUV→RGB via to_format is often unimplemented — blank RGB HUD.
    try:
      return frame.to_format(image.Format.FMT_RGB888)
    except Exception as exc:
      print(f"hud: cannot convert frame ({exc}); RGB blank")
      return image.Image(frame.width(), frame.height(), bg=image.COLOR_BLACK)

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

  def _on_connection_change(self) -> None:
    snap = self._xbox.snapshot()
    if snap.connected and not self._was_connected:
      self._open_checklist()
      threading.Thread(
        target=self._run_peripheral_checklist, daemon=True, name="periph-check",
      ).start()
    if not snap.connected and self._was_connected:
      self._close_checklist()
      self._close_debug()
      if self._debug is not None:
        self._debug.stop_link()
      if self._rear_debug is not None:
        self._rear_debug.stop_link()
    if snap.connected != self._was_connected or snap.busy != self._was_busy:
      self._arm_touch_ignore()
    self._was_connected = snap.connected
    self._was_busy = snap.busy

  def _open_checklist(self) -> None:
    with self._checklist_lock:
      self._checklist = None
      self._checklist_open = True
    if self._camera is not None:
      self._camera.set_paused(True)

  def _close_checklist(self) -> None:
    with self._checklist_lock:
      self._checklist_open = False
      self._checklist = None
    self._arm_touch_ignore()
    if self._xbox.snapshot().connected:
      if self._debug is not None:
        self._debug.start_link()
      if self._rear_debug is not None:
        self._rear_debug.start_link()
    debug_open = self._debug is not None and self._debug.is_open()
    if self._camera is not None and not debug_open:
      self._camera.set_paused(False)

  def _open_debug(self) -> None:
    if self._debug is None:
      return
    if self._camera is not None:
      self._camera.set_paused(True)
    self._debug.open()
    self._arm_touch_ignore()

  def _close_debug(self) -> None:
    if self._debug is None:
      return
    was_open = self._debug.is_open()
    self._debug.close()
    if was_open:
      self._arm_touch_ignore()
    if was_open and self._camera is not None and not self._checklist_open:
      self._camera.set_paused(False)

  def _run_peripheral_checklist(self) -> None:
    """Probe ESP / motors after pad connect; fill the opaque checklist panel."""
    report = self._health.run(
      xbox_connected=True,
      camera_ok=self._camera is not None,
      motion_is_stub=self._rover.is_stub(),
    )
    print("peripheral checklist:")
    for line in report.log_lines():
      print(f"  {line}")
    with self._checklist_lock:
      if self._checklist_open:
        self._checklist = report

  def _request_exit(self) -> None:
    self._xbox.request_stop()
    try:
      self._rover.send_stop()
    except OSError:
      pass
    self._exit.set()
    app.set_exit_flag(True)

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

    with self._checklist_lock:
      checklist_open = self._checklist_open
      checklist_ready = self._checklist is not None
    debug_open = self._debug is not None and self._debug.is_open()

    if checklist_open:
      if checklist_ready and self._checklist_panel.ok_rect().contains(action.x, action.y):
        self._close_checklist()
      elif self._ui.back_rect().contains(action.x, action.y):
        self._request_exit()
      return

    if debug_open and self._debug is not None:
      if self._debug_panel.close_rect().contains(action.x, action.y):
        self._close_debug()
      elif self._debug_panel.ping_rect().contains(action.x, action.y):
        self._debug.run_action(EspDebugAction.PING)
      elif self._debug_panel.stop_rect().contains(action.x, action.y):
        self._debug.run_action(EspDebugAction.STOP)
      elif self._debug_panel.fwd_rect().contains(action.x, action.y):
        self._debug.run_action(EspDebugAction.FWD)
      elif self._debug_panel.init_rect().contains(action.x, action.y):
        self._debug.run_action(EspDebugAction.INIT)
      return

    snap = self._xbox.snapshot()
    if self._ui.back_rect().contains(action.x, action.y):
      self._request_exit()
      return
    if not snap.busy and not snap.connected:
      if self._ui.pair_rect().contains(action.x, action.y):
        self._xbox.start_pairing()
      elif self._ui.connect_rect().contains(action.x, action.y):
        self._xbox.start_connect()
      return
    if snap.connected and self._ui.debug_rect().contains(action.x, action.y):
      self._open_debug()
      return
    if snap.connected and self._ui.disconnect_rect().contains(action.x, action.y):
      self._xbox.request_stop()
      try:
        self._rover.send_stop()
      except OSError:
        pass

  def _send_drive(self, drive) -> None:
    with self._checklist_lock:
      if self._checklist_open:
        return
    if self._debug is not None and self._debug.is_open():
      return
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
