"""Yahboom board stays safe when USB is missing; try_open can recover."""

from __future__ import annotations

from fake_yahboom_drop_on_write_transport import FakeYahboomDropOnWriteTransport
from fake_yahboom_fail_then_ok_transport import FakeYahboomFailThenOkTransport
from lib.motion.chassis_velocity import ChassisVelocity
from lib.yahboom.yahboom_config import YahboomConfig
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard


def test_missing_usb_does_not_crash_on_drive() -> None:
  """Closed board ignores set_velocity / poll (no null-handle USB I/O)."""
  tx = FakeYahboomFailThenOkTransport()
  board = YahboomDriveBoard(tx, YahboomConfig(port="ch340"))
  assert board.try_open() is False
  assert board.is_open is False
  assert "not found" in board.last_error
  board.set_velocity(ChassisVelocity(vx=0.2))
  board.poll()
  assert tx.writes == 0


def test_retry_opens_after_device_appears() -> None:
  """RETRY after plug-in opens the link and allows motion writes."""
  tx = FakeYahboomFailThenOkTransport()
  board = YahboomDriveBoard(tx, YahboomConfig(port="ch340"))
  assert board.try_open() is False
  assert board.try_open() is True
  assert board.is_open is True
  board.set_velocity(ChassisVelocity(vx=0.1))
  assert tx.writes >= 1


def test_io_failure_marks_link_lost() -> None:
  """Mid-session USB I/O error closes the link so the HUD can show RETRY."""
  tx = FakeYahboomDropOnWriteTransport()
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
