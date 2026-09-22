#!/usr/bin/env python3
"""Listen on Maix UART2 while another host triggers ESP Serial output."""

from maix import comm, err, pinmap, time, uart

comm.CommProtocol.set_method("none")
err.check_raise(pinmap.set_pin_function("B0", "UART2_TX"), "B0")
err.check_raise(pinmap.set_pin_function("B1", "UART2_RX"), "B1")
ser = uart.UART("/dev/ttyS2", 115200)
ser.read()
print("LISTENING /dev/ttyS2 for 6 seconds", flush=True)
deadline = time.time() + 6.0
buf = b""
while time.time() < deadline:
  chunk = ser.read()
  if chunk:
    buf += chunk
    print(f"RX {chunk!r}", flush=True)
  else:
    time.sleep_ms(10)
print(f"RESULT {buf!r}", flush=True)
