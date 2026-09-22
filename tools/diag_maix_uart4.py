#!/usr/bin/env python3
"""Maix-side UART4 electrical sanity: pinmap + tx/rx kernel counters."""
from maix import err, pinmap, uart, time


def serial_line(idx: int) -> str:
  lines = open("/proc/tty/driver/serial").read().splitlines()
  # lines[0]=header; port N is often lines[N+1]
  for line in lines:
    if line.startswith(f"{idx}:"):
      return line
  return "?"


def main() -> int:
  print("=== UART4 diag ===")
  for pin, func in (("A21", "UART4_TX"), ("A22", "UART4_RX")):
    r = pinmap.set_pin_function(pin, func)
    print(f"pinmap {pin}->{func}: {r}")
    err.check_raise(r, f"pinmap {pin}")

  print("before:", serial_line(4))
  ser = uart.UART("/dev/ttyS4", 115200)
  time.sleep_ms(100)
  junk = ser.read()
  print("drain:", junk)

  payload = b"PING\n"
  ser.write(payload)
  print(f"wrote {len(payload)} bytes {payload!r}")
  time.sleep_ms(800)
  raw = ser.read()
  print("after:", serial_line(4))
  print("rx:", raw)

  # Second try with write_str
  ser.write_str("HELP\n")
  time.sleep_ms(800)
  raw2 = ser.read()
  print("after HELP:", serial_line(4))
  print("rx2:", raw2)

  if not raw and not raw2:
    print("VERDICT: TX ok, RX empty → ESP silent or wrong wire/GND/power")
    print("Check: A21→Waveshare P_TX, A22→P_RX, common GND, ESP 7-13V")
    print("No system enable needed beyond pinmap (already set).")
    return 2
  print("VERDICT: got RX — link alive")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
