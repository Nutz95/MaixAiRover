#!/usr/bin/env python3
"""Maix UART2 loopback: expects B0 TX shorted to B1 RX."""

from maix import comm, err, pinmap, time, uart

comm.CommProtocol.set_method("none")
err.check_raise(pinmap.set_pin_function("B0", "UART2_TX"), "B0")
err.check_raise(pinmap.set_pin_function("B1", "UART2_RX"), "B1")
ser = uart.UART("/dev/ttyS2", 115200)
time.sleep_ms(100)
ser.read()

payload = b"LOOPBACK123\n"
print(f"TX {payload!r}", flush=True)
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
  print("PASS: Maix UART2 TX+RX alive (loopback)", flush=True)
  raise SystemExit(0)
print("FAIL: no echo — B0/B1 not shorted, or TX dead", flush=True)
raise SystemExit(1)
