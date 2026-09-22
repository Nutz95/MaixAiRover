#!/usr/bin/env python3
"""Maix UART4 loopback: expects A21 TX shorted to A22 RX."""

from maix import comm, err, pinmap, time, uart

comm.CommProtocol.set_method("none")
err.check_raise(pinmap.set_pin_function("A21", "UART4_TX"), "A21")
err.check_raise(pinmap.set_pin_function("A22", "UART4_RX"), "A22")
ser = uart.UART("/dev/ttyS4", 115200)
time.sleep_ms(100)
ser.read()

payload = b"LOOPBACK4\n"
print(f"TX {payload!r} on /dev/ttyS4 A21/A22", flush=True)
ser.write(payload)
deadline = time.time() + 1.5
buf = b""
while time.time() < deadline:
  chunk = ser.read()
  if chunk:
    buf += chunk
    print(f"RX chunk {chunk!r}", flush=True)
    if b"\n" in buf or len(buf) >= len(payload):
      break
  else:
    time.sleep_ms(10)

print(f"RESULT {buf!r}", flush=True)
if payload in buf or buf.strip() == payload.strip():
  print("PASS: Maix UART4 TX+RX alive (loopback)", flush=True)
  raise SystemExit(0)
print("FAIL: no echo — A21/A22 not shorted, or TX dead", flush=True)
raise SystemExit(1)
