"""Teleop-thread tick: config reload, ball toggles, speed, HUD sensors."""

from __future__ import annotations

from maix import time

from lib.ball_follow.ball_follow_runtime import BallFollowRuntime
from lib.config.config_store import ConfigStore
from lib.input.teleop_control_thread import TeleopControlThread
from lib.input.xbox_input_service import XboxInputService
from lib.motion.rover_motion_client import RoverMotionClient
from lib.ui.hud_instruments import HudInstruments, from_telem, from_yahboom
from lib.yahboom.maix_battery_reader import MaixBatteryReader
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard
from lib.esp.esp_debug_session import EspDebugSession


class TeleopTickHandler:
  """Own session speed + HUD sensor cache updates for the control thread."""

  SPEED_DEBOUNCE_MS = 160
  SENSOR_PERIOD_MS = 250

  def __init__(
    self,
    *,
    config_store: ConfigStore,
    xbox: XboxInputService,
    rover: RoverMotionClient,
    ball: BallFollowRuntime,
    control: TeleopControlThread,
    maix_battery: MaixBatteryReader,
    yahboom_board: YahboomDriveBoard | None,
    esp_debug: EspDebugSession | None,
    session_max_speed: int,
    config_max_speed: int,
    speed_step: int,
    send_interval_ms: int,
  ) -> None:
    """Wire dependencies used on each teleop tick."""
    self._config_store = config_store
    self._xbox = xbox
    self._rover = rover
    self._ball = ball
    self._control = control
    self._maix_battery = maix_battery
    self._yahboom_board = yahboom_board
    self._esp_debug = esp_debug
    self.session_max_speed = session_max_speed
    self._config_max_speed = config_max_speed
    self._speed_step = speed_step
    self._send_interval_ms = send_interval_ms
    self._last_speed_change_ms = 0
    self._last_hud_sensor_ms = 0
    self._hud_instruments: HudInstruments = from_telem(None)
    self._maix_battery_pct: int | None = None

  def tick(self) -> None:
    """One control-thread iteration of config / ball / speed / sensors."""
    self._apply_rover_config()
    if self._xbox.consume_mode_toggle():
      self._ball.toggle_mode()
    if self._xbox.consume_color_toggle():
      self._ball.cycle_color()
    self._handle_speed_bumpers()
    self._refresh_hud_sensors()

  def hud_instruments(self) -> HudInstruments:
    """Return the last cached instruments snapshot (draw path safe)."""
    return self._hud_instruments

  def maix_battery_pct(self) -> int | None:
    """Return the last Maix battery percent, if known."""
    return self._maix_battery_pct

  def _apply_rover_config(self) -> None:
    reloaded = self._config_store.reload_if_changed()
    config = self._config_store.get()
    rover_cfg = self._config_store.rover_settings()
    if rover_cfg.max_speed != self._config_max_speed:
      self._config_max_speed = rover_cfg.max_speed
      self.session_max_speed = rover_cfg.max_speed
    self._speed_step = rover_cfg.speed_step
    self._send_interval_ms = rover_cfg.send_interval_ms
    self._rover.set_max_speed(self.session_max_speed)
    self._control.set_send_interval_ms(self._send_interval_ms)
    if reloaded:
      self._ball.apply_config(config)

  def _handle_speed_bumpers(self) -> None:
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
      self.session_max_speed = max(10, self.session_max_speed - self._speed_step)
      changed = True
    if edges.right_bumper:
      self.session_max_speed = min(255, self.session_max_speed + self._speed_step)
      changed = True
    if changed:
      self._last_speed_change_ms = now
      self._rover.set_max_speed(self.session_max_speed)
      print(
        f"speed: {int(self.session_max_speed * 100 / 255)}%"
        f" ({self.session_max_speed}/255)"
      )

  def _refresh_hud_sensors(self) -> None:
    now = time.ticks_ms()
    if now - self._last_hud_sensor_ms < self.SENSOR_PERIOD_MS:
      return
    self._last_hud_sensor_ms = now
    maix_pct = self._maix_battery.percent()
    if self._yahboom_board is not None:
      self._yahboom_board.poll()
      instruments = from_yahboom(
        self._yahboom_board.imu_attitude(),
        self._yahboom_board.battery(),
        maix_pct=maix_pct,
      )
    elif self._esp_debug is not None:
      instruments = from_telem(self._esp_debug.telem(), maix_pct=maix_pct)
    else:
      instruments = from_telem(None, maix_pct=maix_pct)
    self._maix_battery_pct = maix_pct
    self._hud_instruments = instruments
