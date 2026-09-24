#!/usr/bin/env python3
"""Host bench for Yahboom ROS driver board (COM CH340 @ 115200).

Uses vendor Rosmaster_Lib. Open-loop set_motor for per-wheel smoke tests;
auto-report for IMU / encoders / battery.
"""

from __future__ import annotations

import argparse
import sys
import time


def _import_rosmaster():
  try:
    from Rosmaster_Lib import Rosmaster
  except ImportError as exc:
    raise SystemExit(
      "Missing Rosmaster_Lib. Install with:\n"
      "  pip install pyserial\n"
      "  pip install git+https://github.com/Roblibs/Rosmaster_Lib.git\n"
      f"({exc})"
    ) from exc
  return Rosmaster


def open_board(port: str, car_type: int = 1):
  """Open serial, start RX thread, enable auto-report, set mecanum type."""
  Rosmaster = _import_rosmaster()
  board = Rosmaster(car_type=car_type, com=port, debug=False)
  board.create_receive_threading()
  time.sleep(0.15)
  board.set_car_type(car_type)
  board.set_auto_report_state(True, forever=False)
  time.sleep(0.25)
  return board


def cmd_ping(board) -> None:
  """Beep + firmware version + battery (proves TX/RX)."""
  board.set_beep(100)
  time.sleep(0.35)
  version = board.get_version()
  volts = board.get_battery_voltage()
  car = board.get_car_type_from_machine()
  print(f"  beep sent")
  print(f"  firmware version : {version}")
  print(f"  car_type (board) : {car}")
  print(f"  battery          : {volts:.1f} V")
  if version in (0, 0.0) and volts <= 0.0:
    print("  WARN: no telemetry yet - DC IN? switch ON? retry ping.")
  elif volts < 6.0:
    print("  FAIL: battery < 6 V — motors will NOT spin.")
    print("        Connect DC 6-13 V IN and set the board ON/OFF switch to ON.")
    print("        USB alone is enough for IMU, not for motor drivers.")
  else:
    print("  OK: board answering + motor supply looks present.")
  print("  Wiring: Yahboom plug is NOT motor-ribbon order.")
  print("          Board L->R: Mx+ Mx- GND 3.3V HxA HxB")
  print("          Map: Red->Mx+  White->Mx-  Black->GND  Blue->3.3V  Y/G->HxA/HxB")
  print("          See resources/Motors/README.md")


def cmd_status(board) -> None:
  """One-shot snapshot of useful telemetry."""
  time.sleep(0.2)
  version = board.get_version()
  volts = board.get_battery_voltage()
  vx, vy, vz = board.get_motion_data()
  roll, pitch, yaw = board.get_imu_attitude_data(True)
  ax, ay, az = board.get_accelerometer_data()
  gx, gy, gz = board.get_gyroscope_data()
  mx, my, mz = board.get_magnetometer_data()
  m1, m2, m3, m4 = board.get_motor_encoder()
  print(f"  version   : {version}")
  print(f"  battery   : {volts:.1f} V")
  print(f"  motion    : vx={vx:.3f} vy={vy:.3f} vz={vz:.3f}")
  print(f"  attitude  : yaw={yaw:.1f}° roll={roll:.1f}° pitch={pitch:.1f}°")
  print(f"  accel     : ax={ax:.3f} ay={ay:.3f} az={az:.3f}")
  print(f"  gyro      : gx={gx:.3f} gy={gy:.3f} gz={gz:.3f}")
  print(f"  mag       : mx={mx:.1f} my={my:.1f} mz={mz:.1f}")
  print(f"  encoders  : M1={m1} M2={m2} M3={m3} M4={m4}")


def cmd_imu(board, seconds: float) -> None:
  """Stream 9-axis + attitude for a few seconds."""
  end = time.time() + max(0.5, seconds)
  print("  (tilt the board — Ctrl+C to abort)")
  try:
    while time.time() < end:
      ax, ay, az = board.get_accelerometer_data()
      gx, gy, gz = board.get_gyroscope_data()
      mx, my, mz = board.get_magnetometer_data()
      roll, pitch, yaw = board.get_imu_attitude_data(True)
      print(
        f"\r  att y/r/p={yaw:7.1f}/{roll:6.1f}/{pitch:6.1f}"
        f"  a={ax:6.2f},{ay:6.2f},{az:6.2f}"
        f"  g={gx:6.2f},{gy:6.2f},{gz:6.2f}"
        f"  m={mx:6.0f},{my:6.0f},{mz:6.0f}   ",
        end="",
        flush=True,
      )
      time.sleep(0.08)
  except KeyboardInterrupt:
    pass
  print()


def cmd_encoders(board, seconds: float) -> None:
  """Stream encoder counts (spin a wheel by hand to see counts change)."""
  end = time.time() + max(0.5, seconds)
  print("  (spin a motor shaft by hand — Ctrl+C to abort)")
  try:
    while time.time() < end:
      m1, m2, m3, m4 = board.get_motor_encoder()
      print(f"\r  enc M1={m1:8d} M2={m2:8d} M3={m3:8d} M4={m4:8d}   ", end="", flush=True)
      time.sleep(0.08)
  except KeyboardInterrupt:
    pass
  print()


def cmd_battery(board, seconds: float) -> None:
  """Stream battery voltage from auto-report speed frames."""
  end = time.time() + max(0.5, seconds)
  try:
    while time.time() < end:
      volts = board.get_battery_voltage()
      print(f"\r  battery = {volts:.1f} V   ", end="", flush=True)
      time.sleep(0.15)
  except KeyboardInterrupt:
    pass
  print()


def _motor_tuple(index: int, pwm: int) -> tuple[int, int, int, int]:
  speeds = [0, 0, 0, 0]
  speeds[index - 1] = pwm
  return speeds[0], speeds[1], speeds[2], speeds[3]


def cmd_motor(board, index: int, direction: str, pwm: int, seconds: float) -> None:
  """Open-loop PWM one motor: fwd / rev / stop (bench only, no PID)."""
  if index < 1 or index > 4:
    raise SystemExit("motor index must be 1..4")
  sign = {"fwd": 1, "rev": -1, "stop": 0}.get(direction)
  if sign is None:
    raise SystemExit("direction must be fwd|rev|stop")
  duty = 0 if sign == 0 else max(1, min(100, abs(int(pwm)))) * sign
  label = {1: "FR", 2: "FL", 3: "RR", 4: "RL"}.get(index, "?")
  volts = board.get_battery_voltage()
  if duty != 0 and volts < 6.0:
    print(f"  ABORT: battery={volts:.1f} V — need DC 6-13 V IN + switch ON")
    return
  if duty == 0:
    board.set_motor(0, 0, 0, 0)
    print(f"  M{index} ({label}) STOP")
    return
  print(f"  M{index} ({label}) PWM={duty} for {seconds:.1f}s (battery={volts:.1f} V)")
  print("  If it stays still: check M+/M- = Red/White on that MotorN connector.")
  before = board.get_motor_encoder()
  board.set_motor(*_motor_tuple(index, duty))
  try:
    time.sleep(max(0.1, seconds))
  finally:
    board.set_motor(0, 0, 0, 0)
  time.sleep(0.2)
  after = board.get_motor_encoder()
  delta = after[index - 1] - before[index - 1]
  print(f"  stopped. encoder delta M{index} = {delta}")
  if delta == 0:
    print("  encoder still 0: remap pins to board silk M+ M- GND 3V3 HA HB")
    print("  (= Red White Black Blue Yellow Green). Yellow/Green swap alone is not enough.")


def cmd_stop(board) -> None:
  board.set_motor(0, 0, 0, 0)
  print("  all motors STOP")


def cmd_beep(board, ms: int) -> None:
  board.set_beep(max(10, int(ms)))
  print(f"  beep {ms} ms")


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description="Yahboom ROS board USB bench")
  parser.add_argument("--port", default="COM15", help="CH340 COM port (default COM15)")
  parser.add_argument("--pwm", type=int, default=30, help="default open-loop PWM 1..100")
  parser.add_argument("--seconds", type=float, default=1.5, help="motor/stream duration")
  parser.add_argument(
    "action",
    nargs="?",
    default="menu",
    choices=(
      "menu",
      "ping",
      "status",
      "imu",
      "encoders",
      "battery",
      "stop",
      "beep",
      "motor",
    ),
  )
  parser.add_argument("motor", nargs="?", type=int, help="motor 1..4 for action=motor")
  parser.add_argument(
    "direction",
    nargs="?",
    default="fwd",
    choices=("fwd", "rev", "stop"),
    help="for action=motor",
  )
  return parser


def run_action(board, args: argparse.Namespace) -> None:
  action = args.action
  if action == "ping":
    cmd_ping(board)
  elif action == "status":
    cmd_status(board)
  elif action == "imu":
    cmd_imu(board, args.seconds if args.seconds != 1.5 else 5.0)
  elif action == "encoders":
    cmd_encoders(board, args.seconds if args.seconds != 1.5 else 8.0)
  elif action == "battery":
    cmd_battery(board, args.seconds if args.seconds != 1.5 else 5.0)
  elif action == "stop":
    cmd_stop(board)
  elif action == "beep":
    cmd_beep(board, 120)
  elif action == "motor":
    if args.motor is None:
      raise SystemExit("motor action needs index 1..4")
    cmd_motor(board, args.motor, args.direction, args.pwm, args.seconds)
  else:
    raise SystemExit(f"unknown action {action}")


def interactive_menu(board, pwm: int, seconds: float) -> None:
  """Text menu kept open on one serial session."""
  help_text = """
=== Yahboom ROS board bench ===
  1  ping (beep + version + battery)
  2  status snapshot (IMU + encoders + battery + motion)
  3  watch IMU 9-axis (~5s)
  4  watch encoders (~8s) — spin shaft by hand
  5  watch battery (~5s)
  6  motor M1 FR  fwd
  7  motor M1 FR  rev
  8  motor M2 FL  fwd
  9  motor M2 FL  rev
 10  motor M3 RR  fwd
 11  motor M3 RR  rev
 12  motor M4 RL  fwd
 13  motor M4 RL  rev
 14  STOP all motors
 15  beep
  p  change PWM (now {pwm})
  d  change duration seconds (now {seconds})
  q  quit
""".format(pwm=pwm, seconds=seconds)
  while True:
    print(help_text)
    choice = input("choice> ").strip().lower()
    if choice in ("q", "quit", "exit"):
      break
    if choice == "p":
      raw = input(f"pwm 1..100 [{pwm}]> ").strip()
      if raw:
        pwm = max(1, min(100, int(raw)))
      continue
    if choice == "d":
      raw = input(f"seconds [{seconds}]> ").strip()
      if raw:
        seconds = max(0.2, float(raw))
      continue
    try:
      if choice == "1":
        cmd_ping(board)
      elif choice == "2":
        cmd_status(board)
      elif choice == "3":
        cmd_imu(board, 5.0)
      elif choice == "4":
        cmd_encoders(board, 8.0)
      elif choice == "5":
        cmd_battery(board, 5.0)
      elif choice == "6":
        cmd_motor(board, 1, "fwd", pwm, seconds)
      elif choice == "7":
        cmd_motor(board, 1, "rev", pwm, seconds)
      elif choice == "8":
        cmd_motor(board, 2, "fwd", pwm, seconds)
      elif choice == "9":
        cmd_motor(board, 2, "rev", pwm, seconds)
      elif choice == "10":
        cmd_motor(board, 3, "fwd", pwm, seconds)
      elif choice == "11":
        cmd_motor(board, 3, "rev", pwm, seconds)
      elif choice == "12":
        cmd_motor(board, 4, "fwd", pwm, seconds)
      elif choice == "13":
        cmd_motor(board, 4, "rev", pwm, seconds)
      elif choice == "14":
        cmd_stop(board)
      elif choice == "15":
        cmd_beep(board, 120)
      else:
        print("  unknown choice")
    except Exception as exc:
      print(f"  error: {exc}")


def main() -> int:
  args = build_parser().parse_args()
  print(f"Opening {args.port} @ 115200 …")
  board = open_board(args.port)
  try:
    if args.action == "menu":
      interactive_menu(board, args.pwm, args.seconds)
    else:
      run_action(board, args)
  finally:
    try:
      board.set_motor(0, 0, 0, 0)
    except Exception:
      pass
    try:
      board.ser.close()
    except Exception:
      pass
  return 0


if __name__ == "__main__":
  sys.exit(main())
