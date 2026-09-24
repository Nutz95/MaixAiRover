"""Run on MaixCAM2: open Yahboom CH340 and print one battery/IMU sample."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/root/roverMecanum")

from lib.yahboom.ch340_usb_serial import Ch340UsbSerial
from lib.yahboom.yahboom_config import YahboomConfig
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard
from lib.yahboom.maix_battery_reader import MaixBatteryReader


def main() -> int:
  print("maix battery:", MaixBatteryReader().percent())
  transport = Ch340UsbSerial(115200)
  board = YahboomDriveBoard(transport, YahboomConfig(port="ch340"))
  board.initialize()
  time.sleep(0.5)
  for _ in range(10):
    board._poll_rx()
    time.sleep(0.05)
  bat = board.battery()
  imu = board.imu_attitude()
  enc = board.read_encoders()
  print("rover battery:", None if bat is None else f"{bat.volts:.1f} V")
  print("imu:", None if imu is None else f"y={imu.yaw_deg:.1f} p={imu.pitch_deg:.1f} r={imu.roll_deg:.1f}")
  print("enc:", enc)
  board.close()
  print("probe: ok")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
