"""Yahboom board stays safe when USB is missing; try_open can recover."""

from __future__ import annotations

from lib.motion.chassis_velocity import ChassisVelocity
from lib.yahboom.yahboom_config import YahboomConfig
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard


class _FailThenOkTransport:
  """ponytail: first open fails, second succeeds — USB plug-in mid-session."""

  def __init__(self) -> None:
    self.opens = 0
    self.opened = False
    self.writes = 0

  def open(self) -> None:
    self.opens += 1
    if self.opens < 2:
      raise RuntimeError("CH340 1a86:7523 not found (USB host + Yahboom Micro-USB?)")
    self.opened = True

  def close(self) -> None:
    self.opened = False

  def write(self, data: bytes) -> None:
    if not self.opened:
      raise OSError("transport not open")
    self.writes += 1

  def read(self, max_len: int = 256) -> bytes:
    del max_len
    return b""


class _DropOnWriteTransport:
  """Open OK, then fail the next motion write (cable yank / vibration)."""

  def __init__(self) -> None:
    self.opened = False
    self.fail_next_write = False

  def open(self) -> None:
    self.opened = True

  def close(self) -> None:
    self.opened = False

  def write(self, data: bytes) -> None:
    del data
    if not self.opened:
      raise OSError("transport not open")
    if self.fail_next_write:
      self.opened = False
      raise RuntimeError("CH340 bulk OUT failed rc=-4")

  def read(self, max_len: int = 256) -> bytes:
    del max_len
    if not self.opened:
      raise RuntimeError("CH340 bulk IN failed rc=-4")
    return b""


def test_missing_usb_does_not_crash_on_drive() -> None:
  """Closed board ignores set_velocity / poll (no null-handle USB I/O)."""
  tx = _FailThenOkTransport()
  board = YahboomDriveBoard(tx, YahboomConfig(port="ch340"))
  assert board.try_open() is False
  assert board.is_open is False
  assert "not found" in board.last_error
  board.set_velocity(ChassisVelocity(vx=0.2))
  board.poll()
  assert tx.writes == 0


def test_retry_opens_after_device_appears() -> None:
  """RETRY after plug-in opens the link and allows motion writes."""
  tx = _FailThenOkTransport()
  board = YahboomDriveBoard(tx, YahboomConfig(port="ch340"))
  assert board.try_open() is False
  assert board.try_open() is True
  assert board.is_open is True
  board.set_velocity(ChassisVelocity(vx=0.1))
  assert tx.writes >= 1


def test_io_failure_marks_link_lost() -> None:
  """Mid-session USB I/O error closes the link so the HUD can show RETRY."""
  tx = _DropOnWriteTransport()
  board = YahboomDriveBoard(tx, YahboomConfig(port="ch340"))
  assert board.try_open() is True
  tx.fail_next_write = True
  board.set_velocity(ChassisVelocity(vx=0.3))
  assert board.is_open is False
  assert "bulk OUT" in board.last_error
  board.set_velocity(ChassisVelocity(vx=0.5))
  assert board.is_open is False


if __name__ == "__main__":
  test_missing_usb_does_not_crash_on_drive()
  test_retry_opens_after_device_appears()
  test_io_failure_marks_link_lost()
  print("yahboom_drive_link: ok")
