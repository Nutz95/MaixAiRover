import errno
import threading
import traceback

from maix import time

from lib.bluetooth_pairing_service import BluetoothPairingService
from lib.config_store import ConfigStore
from lib.controller_button import ControllerButton
from lib.controller_mapping_engine import ControllerMappingEngine
from lib.controller_state import ControllerState
from lib.evdev_device_finder import EvdevDeviceFinder
from lib.evdev_reader import EvdevReader
from lib.speed_bumper_edges import SpeedBumperEdges
from lib.xbox_snapshot import XboxSnapshot


class XboxInputService:
  """BlueZ in background thread; evdev polled on main loop (MaixPy GIL)."""

  # Stick must settle near center before HUD handoff (raw residual after open).
  _REST_AXIS_MAX = 6000

  def __init__(self, config_store):
    self._config_store = config_store
    self._pairing = BluetoothPairingService(config_store)
    self._finder = EvdevDeviceFinder()
    self._mapper = ControllerMappingEngine(config_store.get())
    self._log_drive_mapping()
    self._lock = threading.Lock()
    self.state = ControllerState()
    self.drive = None
    self.status = "Ready"
    self.progress = 0.0
    self.connected = False
    self.busy = False
    self._stop = threading.Event()
    self._thread = None
    self._reader = None
    self._force_pair = False
    self._handoff = False
    self._pending_speed_lb = False
    self._pending_speed_rb = False
    self._hid_logged = False
    self._pairing.ensure_agent()

  def _log_drive_mapping(self):
    axes = self._config_store.get().get("mapping", {}).get("axes", {})
    print(
      "drive mapping:"
      f" forward={axes.get('drive_forward', 'left_y')}"
      f" strafe={axes.get('drive_strafe', 'trigger_diff')}"
      f" spin={axes.get('drive_spin', axes.get('drive_rotate', 'right_x'))}"
      f" pivot={axes.get('drive_pivot', 'left_x')}"
    )

  def consume_speed_edges(self) -> SpeedBumperEdges:
    """LB/RB press edges for session max_speed (one shot per physical press)."""
    with self._lock:
      edges = SpeedBumperEdges(
        left_bumper=self._pending_speed_lb,
        right_bumper=self._pending_speed_rb,
      )
      self._pending_speed_lb = False
      self._pending_speed_rb = False
    return edges

  def snapshot(self) -> XboxSnapshot:
    """Return an immutable snapshot for the UI and control loop."""
    with self._lock:
      return XboxSnapshot(
        status=self.status,
        connected=self.connected,
        busy=self.busy,
        state=self.state.copy(),
        drive=self.drive,
        progress=self.progress,
      )

  def poll(self):
    """Drain evdev on main thread — call every control-loop iteration."""
    self._config_store.reload_if_changed()
    with self._lock:
      if not self._handoff or self._reader is None:
        return
      reader = self._reader
    try:
      reader.poll_inputs()
      if reader.event_count and not self._hid_logged:
        self._hid_logged = True
        print(f"input: HID reports flowing ({reader.event_count})")
      live = reader.state.copy()
      self._mapper.update_config(self._config_store.get())
      drive = self._mapper.compute(live)
      speed_lb = reader.state.take_edge(ControllerButton.LB)
      speed_rb = reader.state.take_edge(ControllerButton.RB)
      reader.state.pressed_edge.clear()
      with self._lock:
        self.state = live
        self.drive = drive
        if speed_lb:
          self._pending_speed_lb = True
        if speed_rb:
          self._pending_speed_rb = True
    except OSError as exc:
      if exc.errno in (errno.ENODEV, errno.ENOENT):
        self._on_reader_lost("Controller disconnected")
      else:
        raise

  def start_connect(self):
    """Start a background CONNECT to the saved controller MAC."""
    with self._lock:
      if self.connected or self.busy:
        return
    self._start_worker(force_pair=False)

  def start_pairing(self):
    """Start a background PAIR (remove bond + encrypted re-pair)."""
    with self._lock:
      if self.busy:
        return
    self._start_worker(force_pair=True)

  def _start_worker(self, force_pair):
    if self._thread and self._thread.is_alive():
      return
    self._stop.clear()
    self._handoff = False
    with self._lock:
      self.busy = True
      self.connected = False
      self.drive = None
      self.progress = 0.05
    self._force_pair = force_pair
    self._set_status("Pairing (hold SYNC)..." if force_pair else "Connecting...")
    self._thread = threading.Thread(target=self._worker, daemon=True)
    self._thread.start()

  def request_stop(self):
    """Drop the live HID session and mark the pad disconnected."""
    self._stop.set()
    self._close_reader()
    with self._lock:
      self.connected = False
      self.drive = None
      if self.status == "Connected — drive":
        self.status = "Ready"

  def close(self) -> None:
    """Stop evdev and the BlueZ agent (app shutdown)."""
    self.request_stop()
    self._pairing.close()

  def _set_status(self, status, progress=None):
    with self._lock:
      self.status = status
      if progress is not None:
        self.progress = float(progress)

  def _set_connected(self, connected):
    with self._lock:
      self.connected = connected

  def _close_reader(self):
    with self._lock:
      reader = self._reader
      self._reader = None
      self._handoff = False
      self._hid_logged = False
    if reader is not None:
      reader.close()

  def _on_reader_lost(self, status):
    self._close_reader()
    with self._lock:
      self.connected = False
      self.drive = None
      self.status = status

  def _worker(self):
    handed_off = False
    try:
      self._mapper.update_config(self._config_store.get())

      if self._force_pair:
        self._set_status("Pairing (hold SYNC)...", 0.1)
        scan = self._pairing.scan_for_controller()
        if not scan.ok():
          self._set_status(scan.error, 0.0)
          return
        if self._stop.is_set():
          return
        self._set_status("Bonding Xbox...", 0.45)
        result = self._pairing.pair_mac(scan.mac)
        print("--- bluetoothctl ---")
        print(result.output)
        if not result.ok():
          self._set_status(result.error, 0.0)
          return
        self._set_status("Opening input...", 0.8)
        handed_off = self._claim_hid()
        return

      # CONNECT never disconnects: a failed reconnect must not power off the pad.
      with self._lock:
        already = self._handoff and self._reader is not None
      if already:
        return
      self._set_status("Connecting...", 0.2)
      ev_path = self._finder.find_xbox_event()
      if ev_path and self._can_open(ev_path):
        print(f"input already present: {ev_path}")
        handed_off = self._open_evdev(ev_path)
        if handed_off:
          return
        print("input: event node unusable — trying BlueZ connect")

      self._set_status("Waiting Xbox (agent on)...", 0.4)
      ev_path = self._wait_for_input(timeout_ms=5000)
      if ev_path:
        handed_off = self._open_evdev(ev_path)
        if handed_off:
          return

      self._set_status("BlueZ connect...", 0.6)
      result = self._pairing.connect_saved()
      print("--- bluetoothctl ---")
      print(result.output)
      self._set_status("Opening input...", 0.85)
      handed_off = self._claim_hid()
      if handed_off:
        return
      if not result.ok():
        self._set_status(result.error, 0.0)

    except OSError as exc:
      if exc.errno in (errno.ENODEV, errno.ENOENT):
        self._set_status("Controller disconnected")
      else:
        self._set_status(f"Erreur: {exc}")
        print(exc)
        traceback.print_exc()
    except Exception as exc:
      self._set_status(f"Erreur: {exc}")
      print(exc)
      traceback.print_exc()
    finally:
      with self._lock:
        self.busy = False
        if not handed_off:
          self.connected = False
          self.drive = None
          self.progress = 0.0
          if self.status.startswith("Erreur") or self.status in (
            "Connecting...",
            "Pairing (hold SYNC)...",
            "Pairing...",
            "Waiting Xbox (agent on)...",
            "Waiting Xbox input...",
            "Bonding Xbox...",
            "Opening input...",
            "BlueZ connect...",
          ):
            self.status = "Ready"
      if not handed_off:
        self._close_reader()

  def _claim_hid(self) -> bool:
    """Wait for and open the Xbox evdev node without disconnecting it."""
    if self._stop.is_set():
      return False
    ev_path = self._wait_for_input(timeout_ms=12000)
    if ev_path and self._open_evdev(ev_path):
      return True
    self._set_status("Xbox input unavailable")
    return False

  def _wait_for_input(self, timeout_ms: int = 15000):
    """Wait until /dev/input/event* for the Xbox can be opened."""
    self._set_status("Waiting Xbox input...")
    deadline = time.ticks_ms() + timeout_ms
    while time.ticks_ms() < deadline and not self._stop.is_set():
      ev_path = self._finder.find_xbox_event()
      if ev_path and self._can_open(ev_path):
        return ev_path
      time.sleep_ms(250)
    self._finder.list_devices()
    self._set_status("Input Xbox absent")
    return None

  def _can_open(self, ev_path):
    try:
      f = open(ev_path, "rb")
      f.close()
      return True
    except OSError:
      return False

  def _open_evdev(self, ev_path):
    reader = None
    for attempt in range(8):
      if self._stop.is_set():
        return False
      if not self._can_open(ev_path):
        print(f"evdev open retry {attempt + 1}/8: {ev_path} not ready")
        time.sleep_ms(250)
        ev_path = self._finder.find_xbox_event() or ev_path
        continue
      try:
        reader = EvdevReader(ev_path, self._config_store.get())
        reader.open()
        break
      except OSError as exc:
        if exc.errno not in (errno.ENODEV, errno.ENOENT):
          raise
        print(f"evdev open retry {attempt + 1}/8: {ev_path} ({exc})")
        time.sleep_ms(250)
        ev_path = self._finder.find_xbox_event() or ev_path
    else:
      self._set_status("Input open failed")
      return False

    deadline = time.ticks_ms() + 1500
    while not reader.kernel_state_available and time.ticks_ms() < deadline:
      reader.poll_inputs()
      time.sleep_ms(50)
    if not reader.kernel_state_available:
      reader.close()
      self._set_status("Xbox input state unavailable", 0.0)
      print("input: event node opened but EVIOCGABS is unavailable")
      return False

    # Wait until sticks report near rest — first ABS values are often garbage.
    rest_deadline = time.ticks_ms() + 2500
    while time.ticks_ms() < rest_deadline and not self._stop.is_set():
      reader.poll_inputs()
      if self._sticks_at_rest(reader.state):
        break
      time.sleep_ms(40)
    else:
      reader.poll_inputs()
      print(
        "input: stick rest settle timeout"
        f" L=({reader.state.left_x},{reader.state.left_y})"
        f" R=({reader.state.right_x},{reader.state.right_y})"
      )

    with self._lock:
      self._reader = reader
      self._handoff = True
      self.connected = True
      self.status = "Connected — drive"
      self.progress = 1.0
    reader.poll_inputs()
    live = reader.state.copy()
    drive = self._mapper.compute(live)
    with self._lock:
      self.state = live
      self.drive = drive
    print(
      f"input: {ev_path} ready"
      f" L=({live.left_x},{live.left_y}) R=({live.right_x},{live.right_y})"
      f" events={reader.event_count}"
    )
    return True

  def _sticks_at_rest(self, state) -> bool:
    limit = self._REST_AXIS_MAX
    return (
      abs(state.left_x) <= limit
      and abs(state.left_y) <= limit
      and abs(state.right_x) <= limit
      and abs(state.right_y) <= limit
    )
