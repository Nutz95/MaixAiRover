"""Serial session wrapper around Yahboom Rosmaster_Lib."""

from __future__ import annotations

import threading
import time

from yahboom_debug.dummy_serial import DummySerial
from yahboom_debug.guarded_serial import GuardedSerial


class YahboomBoardSession:
  """Own one Rosmaster connection for the debug UI."""

  MOTOR_LABELS = ("FL", "RL", "FR", "RR")  # M1..M4 per Yahboom firmware docs

  def __init__(self) -> None:
    """Create a disconnected session."""
    self._board = None
    self._port = ""
    self._lock = threading.Lock()
    self._error = ""
    self._car_type = 1
    self._car_type_reported = -1

  @property
  def connected(self) -> bool:
    """True when a board handle is open and the serial port is alive."""
    board = self._board
    if board is None:
      return False
    ser = getattr(board, "ser", None)
    if ser is None:
      return False
    try:
      if hasattr(ser, "is_open"):
        return bool(ser.is_open)
      if hasattr(ser, "isOpen"):
        return bool(ser.isOpen())
    except Exception:
      return False
    return True

  @property
  def has_handle(self) -> bool:
    """True if we still own a board object (may be a dead serial)."""
    return self._board is not None

  def reclaim_if_dead(self) -> bool:
    """If serial died, drop the handle. Returns True when a drop happened."""
    if self._board is not None and not self.connected:
      self.disconnect()
      return True
    return False

  @property
  def port(self) -> str:
    """Last connected COM port."""
    return self._port

  @property
  def error(self) -> str:
    """Last connect/IO error message."""
    return self._error

  @property
  def car_type(self) -> int:
    """Car type sent to the board (1=X3 mecanum)."""
    return self._car_type

  @property
  def car_type_reported(self) -> int:
    """Car type read back from MCU (-1 if unknown)."""
    return self._car_type_reported

  def connect(self, port: str, car_type: int = 1) -> None:
    """Open serial, enable auto-report, set mecanum car type."""
    self.disconnect()
    time.sleep(0.25)  # Windows needs a beat to release the COM handle.
    try:
      from Rosmaster_Lib import Rosmaster
    except ImportError as exc:
      self._error = (
        "Rosmaster_Lib missing — pip install pyserial and "
        "git+https://github.com/Roblibs/Rosmaster_Lib.git"
      )
      raise RuntimeError(self._error) from exc
    board = None
    try:
      board = Rosmaster(car_type=car_type, com=port, debug=False)
      # Wrap before the RX thread starts so Close cannot IndexError on empty read.
      board.ser = GuardedSerial(board.ser)
      board.create_receive_threading()
      time.sleep(0.15)
      board.set_car_type(car_type)
      board.set_auto_report_state(True, forever=False)
      time.sleep(0.2)
      reported = -1
      try:
        reported = int(board.get_car_type_from_machine())
      except Exception:
        reported = -1
      with self._lock:
        self._board = board
        self._port = port
        self._car_type = int(car_type)
        self._car_type_reported = reported
        self._error = ""
      board = None  # ownership transferred
    except Exception as connect_error:
      self._error = str(connect_error)
      if board is not None:
        self._close_board(board)
      raise RuntimeError(self._error) from connect_error

  def disconnect(self) -> None:
    """Stop motors, close the COM port, drop the board handle."""
    with self._lock:
      board = self._board
      self._board = None
    if board is None:
      return
    try:
      board.set_motor(0, 0, 0, 0)
      board.set_car_motion(0.0, 0.0, 0.0)
    except Exception as stop_error:
      print(f"yahboom: stop on disconnect: {stop_error}")
    self._close_board(board)
    self._port = ""

  @staticmethod
  def _close_board(board) -> None:
    """Release serial so reconnect can open the same COM again.

    Rosmaster.__receive_data does ``bytearray(ser.read())[0]`` with no empty
    check — closing the port makes ``read()`` return ``b''`` and crashes the
    daemon thread. ``GuardedSerial.close`` parks that thread instead.
    """
    ser = getattr(board, "ser", None)
    if ser is not None:
      try:
        ser.close()
      except Exception as close_error:
        print(f"yahboom: ser.close: {close_error}")
    # Avoid AttributeError spam in Rosmaster.__del__ after failed opens.
    board.ser = DummySerial()

  def stop_all(self) -> None:
    """Emergency stop: open-loop PWM and chassis velocity."""
    board = self._require()
    with self._lock:
      board.set_motor(0, 0, 0, 0)
      board.set_car_motion(0.0, 0.0, 0.0)

  def set_car_motion(self, vx: float, vy: float, vz: float) -> None:
    """Closed-loop body velocity (m/s, m/s, rad/s)."""
    board = self._require()
    with self._lock:
      board.set_car_motion(float(vx), float(vy), float(vz))

  def set_motor_pwm(self, index: int, pwm: int) -> None:
    """Open-loop one motor (1..4), others forced to 0. PWM in [-100, 100]."""
    if index < 1 or index > 4:
      raise ValueError("motor index must be 1..4")
    duty = max(-100, min(100, int(pwm)))
    speeds = [0, 0, 0, 0]
    speeds[index - 1] = duty
    board = self._require()
    with self._lock:
      board.set_motor(*speeds)

  def battery_v(self) -> float:
    """Latest battery voltage (0 if unknown)."""
    board = self._require()
    with self._lock:
      return float(board.get_battery_voltage())

  def encoders(self) -> tuple[int, int, int, int]:
    """M1..M4 encoder counts."""
    board = self._require()
    with self._lock:
      m1, m2, m3, m4 = board.get_motor_encoder()
      return int(m1), int(m2), int(m3), int(m4)

  def beep(self, ms: int = 80) -> None:
    """Short beep."""
    board = self._require()
    with self._lock:
      board.set_beep(max(10, int(ms)))

  def _require(self):
    if not self.connected:
      self._board = None
      raise RuntimeError("Board not connected")
    return self._board
