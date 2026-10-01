"""Host checks for EspLinkConfig + DualBoardDrivePort."""

from __future__ import annotations

from fake_pair_drive_front import FakePairDriveFront
from fake_pair_drive_rear import FakePairDriveRear
from lib.motion.dual_board_drive_port import DualBoardDrivePort
from lib.esp.esp_link_config import EspLinkConfig
from lib.esp.esp_pair_drive_board import EspPairDriveBoard
from lib.motion.null_rear_drive_board import NullRearDriveBoard
from lib.motion.wheel_speeds import WheelSpeeds


def test_dual_board_splits_front_rear() -> None:
  front = FakePairDriveFront()
  rear = NullRearDriveBoard()
  port = DualBoardDrivePort(front, rear)
  port.set_wheel_speeds(
    WheelSpeeds(front_left=20, front_right=-15, rear_left=9, rear_right=-9)
  )
  assert front.pairs[-1] == (20, -15)
  port.stop()
  assert front.stopped == 1
  enc = port.read_encoders()
  assert enc.m1 == 1 and enc.m2 == 2 and enc.m3 == 0 and enc.m4 == 0


def test_dual_board_live_rear() -> None:
  front = FakePairDriveFront()
  rear = FakePairDriveRear()
  port = DualBoardDrivePort(front, rear)
  port.set_wheel_speeds(
    WheelSpeeds(front_left=10, front_right=11, rear_left=12, rear_right=13)
  )
  assert front.pairs[-1] == (10, 11)
  assert rear.pairs[-1] == (12, 13)
  enc = port.read_encoders()
  assert enc.m1 == 1 and enc.m2 == 2 and enc.m3 == 3 and enc.m4 == 4


def test_esp_link_config_legacy_and_nested() -> None:
  legacy = EspLinkConfig.from_mapping(
    {"uart_port": "uart4", "wifi_host": "192.168.20.148", "wifi_port": 2333}
  )
  assert legacy.front.uart_port == "uart4"
  assert legacy.front.wifi_host == "192.168.20.148"
  assert legacy.rear is None

  nested = EspLinkConfig.from_mapping(
    {
      "front": {"uart_port": "uart4", "wifi_host": "192.168.20.148"},
      "rear": {"uart_port": "uart2", "wifi_host": ""},
    }
  )
  assert nested.front.uart_port == "uart4"
  assert nested.rear is not None
  assert nested.rear.uart_port == "uart2"


def test_pair_board_stop_burst() -> None:
  sent = []

  def set_drive(left: int, right: int) -> None:
    sent.append((left, right))

  board = EspPairDriveBoard(set_drive, max_setpoint=50)
  board.set_pair(10, -10)
  board.set_pair(0, 0)
  assert sent[0] == (10, -10)
  assert sent[1] == (0, 0)
  board.set_pair(0, 0)
  assert len(sent) >= 3


def main() -> None:
  test_dual_board_splits_front_rear()
  test_dual_board_live_rear()
  test_esp_link_config_legacy_and_nested()
  test_pair_board_stop_burst()
  print("dual_board_drive: ok")


if __name__ == "__main__":
  main()
