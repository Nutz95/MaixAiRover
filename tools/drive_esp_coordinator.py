#!/usr/bin/env python3
"""PC smoke: drive Hiwonder via Waveshare ESP coordinator (UART).

Flash esp32/rover_coordinator first, then:

  python tools/drive_esp_coordinator.py --port COM9 --demo
  python tools/drive_esp_coordinator.py --port COM9 --speed 30 0 0 0 --hold 2
  python tools/drive_esp_coordinator.py --port COM9   # interactive REPL
"""

from __future__ import annotations

import argparse
import sys
import time

import serial


def _safe_print(prefix: str, line: str) -> None:
  text = f"{prefix}{line}"
  try:
    print(text)
  except UnicodeEncodeError:
    print(text.encode("ascii", errors="replace").decode("ascii"))


def _read_ok(ser: serial.Serial, timeout_s: float = 2.0) -> str:
  deadline = time.monotonic() + timeout_s
  while time.monotonic() < deadline:
    line = ser.readline().decode("utf-8", errors="replace").strip()
    if not line:
      continue
    _safe_print("< ", line)
    if line.startswith("OK ") or line.startswith("ERR "):
      return line
  raise TimeoutError("no OK/ERR from ESP32")


def cmd(ser: serial.Serial, text: str, timeout_s: float = 2.0) -> str:
  _safe_print("> ", text)
  ser.write((text + "\n").encode("ascii"))
  ser.flush()
  return _read_ok(ser, timeout_s=timeout_s)


def drain_boot(ser: serial.Serial, seconds: float = 2.5) -> None:
  deadline = time.monotonic() + seconds
  while time.monotonic() < deadline:
    line = ser.readline().decode("utf-8", errors="replace").strip()
    if line:
      _safe_print("< ", line)


def run_demo(ser: serial.Serial, channel: int, speed: int, hold_s: float) -> None:
  """Spin one motor forward, reverse, then stop."""
  if channel < 1 or channel > 4:
    raise SystemExit("channel must be 1..4")
  speeds = [0, 0, 0, 0]
  speeds[channel - 1] = speed
  cmd(ser, "INIT", timeout_s=3.0)
  cmd(ser, "BAT")
  cmd(ser, "ENC")
  cmd(ser, f"SPEED {speeds[0]} {speeds[1]} {speeds[2]} {speeds[3]}")
  end = time.monotonic() + hold_s
  while time.monotonic() < end:
    time.sleep(0.4)
    cmd(ser, f"SPEED {speeds[0]} {speeds[1]} {speeds[2]} {speeds[3]}")
  speeds[channel - 1] = -speed
  end = time.monotonic() + hold_s
  while time.monotonic() < end:
    cmd(ser, f"SPEED {speeds[0]} {speeds[1]} {speeds[2]} {speeds[3]}")
    time.sleep(0.4)
  cmd(ser, "STOP")
  cmd(ser, "ENC")
  print("demo done")


def run_hold(ser: serial.Serial, speeds: list[int], hold_s: float) -> None:
  cmd(ser, f"SPEED {speeds[0]} {speeds[1]} {speeds[2]} {speeds[3]}")
  end = time.monotonic() + hold_s
  while time.monotonic() < end:
    time.sleep(0.4)
    cmd(ser, f"SPEED {speeds[0]} {speeds[1]} {speeds[2]} {speeds[3]}")
  cmd(ser, "STOP")


def repl(ser: serial.Serial) -> None:
  print("REPL: PING INIT STOP SPEED m1 m2 m3 m4 PWM BAT ENC WIFI  (Ctrl+C quit)")
  while True:
    try:
      line = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
      print()
      break
    if not line:
      continue
    try:
      cmd(ser, line, timeout_s=3.0)
    except TimeoutError as exc:
      print(exc)
  try:
    cmd(ser, "STOP")
  except Exception:
    pass


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--port", default="COM9", help="Waveshare ESP32 UART COM port")
  p.add_argument("--baud", type=int, default=115200)
  p.add_argument("--demo", action="store_true", help="spin one motor fwd/rev")
  p.add_argument("--channel", type=int, default=1, help="motor 1..4 for --demo")
  p.add_argument("--demo-speed", type=int, default=30, help="closed-loop setpoint")
  p.add_argument("--hold", type=float, default=2.0, help="seconds per phase")
  p.add_argument(
    "--speed",
    nargs=4,
    type=int,
    metavar=("M1", "M2", "M3", "M4"),
    help="one-shot SPEED then hold then STOP",
  )
  args = p.parse_args()

  ser = serial.Serial(args.port, args.baud, timeout=0.2)
  time.sleep(0.3)
  drain_boot(ser)
  try:
    cmd(ser, "PING")
  except TimeoutError:
    print(
      "ESP not answering PING — close monitor, reset board, check COM",
      file=sys.stderr,
    )
    return 1

  if args.demo:
    run_demo(ser, args.channel, args.demo_speed, args.hold)
  elif args.speed is not None:
    run_hold(ser, list(args.speed), args.hold)
  else:
    repl(ser)

  ser.close()
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
