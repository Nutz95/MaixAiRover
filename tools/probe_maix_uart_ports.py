#!/usr/bin/env python3
"""Maix UART port sweep: UART4 (A21/A22) and UART2 (B0/B1) + optional loopback note.

  python3 /tmp/probe_maix_uart_ports.py
  python3 /tmp/probe_maix_uart_ports.py --loopback-hint
"""

from __future__ import annotations

import argparse
import time

from maix import err, pinmap, uart


PORTS = (
  {
    "name": "UART4",
    "device": "/dev/ttyS4",
    "tx_pin": "A21",
    "tx_fn": "UART4_TX",
    "rx_pin": "A22",
    "rx_fn": "UART4_RX",
  },
  {
    "name": "UART2",
    "device": "/dev/ttyS2",
    "tx_pin": "B0",
    "tx_fn": "UART2_TX",
    "rx_pin": "B1",
    "rx_fn": "UART2_RX",
  },
)


def serial_stats(idx: int) -> str:
  for line in open("/proc/tty/driver/serial"):
    if line.startswith(f"{idx}:"):
      return line.strip()
  return "?"


def try_port(p: dict, timeout_s: float = 1.5) -> None:
  name = p["name"]
  print(f"\n=== {name} {p['tx_pin']}/{p['rx_pin']} -> {p['device']} ===")
  for pin, fn in ((p["tx_pin"], p["tx_fn"]), (p["rx_pin"], p["rx_fn"])):
    r = pinmap.set_pin_function(pin, fn)
    print(f"  pinmap {pin}->{fn}: {r}")
    err.check_raise(r, f"pinmap {pin}")

  # ttyS number from device path
  idx = int(p["device"].replace("/dev/ttyS", ""))
  print(f"  before: {serial_stats(idx)}")
  ser = uart.UART(p["device"], 115200)
  time.sleep(0.1)
  ser.read()
  ser.write_str("PING\n")
  deadline = time.time() + timeout_s
  buf = b""
  while time.time() < deadline:
    chunk = ser.read()
    if chunk:
      buf += chunk
      if b"\n" in buf:
        break
    else:
      time.sleep(0.02)
  print(f"  after:  {serial_stats(idx)}")
  print(f"  rx: {buf!r}")
  if buf:
    text = buf.decode("utf-8", errors="replace")
    print(f"  text: {text.strip()!r}")
    if "OK " in text or "PONG" in text:
      print(f"  PASS {name}")
      return
  print(f"  FAIL {name}: no reply (TX may still have incremented)")


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--loopback-hint", action="store_true")
  args = ap.parse_args()
  print("NOTE: WiFi PING earlier proved ESP firmware, NOT that UART RX got bytes.")
  print("Wire MUST be crossed: Maix TX -> Waveshare RX, Maix RX -> Waveshare TX, GND.")
  print("Silkscreen TX/RX = board signals. Same-label TX->TX will continuity-beep but not talk.")
  for p in PORTS:
    try:
      try_port(p)
    except Exception as exc:
      print(f"  ERROR {p['name']}: {exc}")
  if args.loopback_hint:
    print("\nLoopback check (Maix alone): short A21<->A22, rerun UART4;")
    print("if rx echoes PING, Maix RX path is fine → fault is Waveshare side / cross.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
