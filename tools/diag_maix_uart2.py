#!/usr/bin/env python3
from maix import err, pinmap, uart, time


def sl(i: int) -> str:
  for line in open("/proc/tty/driver/serial"):
    if line.startswith(f"{i}:"):
      return line.strip()
  return "?"


print("before", sl(2))
err.check_raise(pinmap.set_pin_function("B0", "UART2_TX"), "tx")
err.check_raise(pinmap.set_pin_function("B1", "UART2_RX"), "rx")
ser = uart.UART("/dev/ttyS2", 115200)
time.sleep_ms(100)
ser.read()
ser.write_str("PING\n")
time.sleep_ms(800)
print("after", sl(2))
print("rx", ser.read())
