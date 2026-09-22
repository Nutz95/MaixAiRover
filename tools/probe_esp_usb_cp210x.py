#!/usr/bin/env python3
"""Probe Waveshare ESP over USB CP210x (Maix host) using userspace libusb.

Run ON MaixCAM2 (USB Settings = Host, ESP plugged into Maix USB-C):

  python3 /tmp/probe_esp_usb_cp210x.py
"""

from __future__ import annotations

import sys
import time

# Allow drop-in under /tmp or repo lib/.
sys.path.insert(0, "/root/roverMecanum")
sys.path.insert(0, "/tmp")

from lib.cp210x_usb_serial import Cp210xUsbSerial  # noqa: E402


def _cmd(port: Cp210xUsbSerial, line: str, timeout_s: float = 2.0) -> str:
  print(f"> {line}")
  port.write_str(line + "\n")
  deadline = time.time() + timeout_s
  buf = b""
  while time.time() < deadline:
    chunk = port.read(256, timeout_ms=50)
    if chunk:
      buf += chunk
      while b"\n" in buf:
        raw, buf = buf.split(b"\n", 1)
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
          continue
        print(f"< {text}")
        if text.startswith("OK ") or text.startswith("ERR "):
          return text
    time.sleep(0.02)
  print(f"  raw_rx={buf!r}")
  raise TimeoutError(f"no OK/ERR for {line!r}")


def main() -> int:
  port = Cp210xUsbSerial(115200)
  try:
    port.open()
  except RuntimeError as exc:
    print(f"FAIL open: {exc}")
    return 1
  try:
    # Drain boot noise.
    time.sleep(0.15)
    port.read(512, timeout_ms=100)
    pong = _cmd(port, "PING")
    scan = _cmd(port, "SCAN")
    bat = _cmd(port, "BAT")
  except Exception as exc:
    print(f"FAIL: {exc}")
    return 2
  finally:
    port.close()

  print("---")
  print(f"{pong} | {scan} | {bat}")
  if pong.startswith("OK ") and "motor=1" in scan:
    print("PASS: USB CP210x userspace link + Hiwonder present")
    return 0
  if pong.startswith("OK "):
    print("PARTIAL: USB link OK, motors missing (VM / I2C?)")
    return 3
  print("FAIL")
  return 4


if __name__ == "__main__":
  raise SystemExit(main())
