#!/usr/bin/env python3
"""Run ON MaixCAM2: probe Waveshare ESP over a chosen UART (text + binary).

IMPORTANT: Maix firmware may print \"Maix Comm Protocol ... uart4(/dev/ttyS4)\"
even when WE use uart2 — that is system noise. This script disables it and
prints the real /proc ttyS* counters for the port we opened.
"""

from __future__ import annotations

import argparse
import socket
import struct
import time

# Disable system CommProtocol BEFORE importing uart (avoids fake ttyS4 noise).
try:
  from maix import comm

  comm.CommProtocol.set_method("none")
except Exception as exc:
  print(f"(warn) CommProtocol disable: {exc}")

from maix import err, pinmap, uart

SYNC = 0xA5
CMD_PING = 0x01
CMD_TELEM = 0x10
RSP_PONG = 0x81
RSP_TELEM = 0x90

PORTS = {
  "uart4": {
    "device": "/dev/ttyS4",
    "tty_idx": 4,
    "pins": (("A21", "UART4_TX"), ("A22", "UART4_RX")),
  },
  "uart2": {
    "device": "/dev/ttyS2",
    "tty_idx": 2,
    "pins": (("B0", "UART2_TX"), ("B1", "UART2_RX")),
  },
}


def _crc8(data: bytes) -> int:
  return sum(data) & 0xFF


def _encode(msg_type: int, payload: bytes = b"") -> bytes:
  body = bytes((msg_type & 0xFF, len(payload))) + payload
  return bytes((SYNC,)) + body + bytes((_crc8(body),))


def _tty_line(idx: int) -> str:
  for line in open("/proc/tty/driver/serial"):
    if line.startswith(f"{idx}:"):
      return line.strip()
  return f"{idx}: ?"


def _open_uart(port: str) -> tuple[uart.UART, dict]:
  key = (port or "uart2").strip().lower()
  if key not in PORTS:
    raise ValueError(f"unknown port {port!r}; use uart2 or uart4")
  cfg = PORTS[key]
  print("=" * 60)
  print(f"USING PORT={key}  DEVICE={cfg['device']}  (NOT ttyS4 unless port=uart4)")
  print(f"PINS={cfg['pins']}")
  print("=" * 60)
  for pin, func in cfg["pins"]:
    err.check_raise(pinmap.set_pin_function(pin, func), f"pinmap {pin}->{func}")
    print(f"  pinmap OK {pin} -> {func}")
  print(f"  before {_tty_line(cfg['tty_idx'])}")
  ser = uart.UART(cfg["device"], 115200)
  time.sleep(0.2)
  for _ in range(10):
    chunk = ser.read()
    if not chunk:
      break
    time.sleep(0.02)
  return ser, cfg


def _cmd_text(ser: uart.UART, line: str, cfg: dict, timeout_s: float = 2.0) -> str:
  print(f"> {line}  via {cfg['device']}")
  before = _tty_line(cfg["tty_idx"])
  ser.write_str(line + "\n")
  deadline = time.time() + timeout_s
  buf = b""
  while time.time() < deadline:
    chunk = ser.read()
    if chunk:
      buf += chunk
      while b"\n" in buf:
        raw, buf = buf.split(b"\n", 1)
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
          continue
        print(f"< {text}")
        print(f"  after  {_tty_line(cfg['tty_idx'])}")
        if text.startswith("OK ") or text.startswith("ERR "):
          return text
    else:
      time.sleep(0.02)
  print(f"  before {before}")
  print(f"  after  {_tty_line(cfg['tty_idx'])}")
  print(f"  raw_rx={buf!r}")
  raise TimeoutError(
    f"no OK/ERR on {cfg['device']} — use Maix TX→P_TX, RX→P_RX + GND"
  )


def _cmd_bin(ser: uart.UART, msg_type: int, payload: bytes = b"", timeout_s: float = 2.0):
  frame = _encode(msg_type, payload)
  print(f"> bin 0x{msg_type:02X} ({len(frame)} B)")
  ser.write(frame)
  deadline = time.time() + timeout_s
  buf = b""
  while time.time() < deadline:
    chunk = ser.read()
    if chunk:
      buf += chunk
      while True:
        start = buf.find(bytes((SYNC,)))
        if start < 0:
          buf = b""
          break
        if start > 0:
          buf = buf[start:]
        if len(buf) < 4:
          break
        length = buf[2]
        need = 3 + length + 1
        if len(buf) < need:
          break
        body = buf[1 : 3 + length]
        crc = buf[3 + length]
        buf = buf[need:]
        if crc != _crc8(body):
          continue
        rsp_type = body[0]
        rsp_payload = body[2:]
        print(f"< bin 0x{rsp_type:02X} len={len(rsp_payload)}")
        return rsp_type, rsp_payload
    else:
      time.sleep(0.02)
  print(f"  raw_rx={buf!r}")
  raise TimeoutError(f"no binary reply for 0x{msg_type:02X}")


def _cmd_wifi(host: str, port: int, line: str, timeout_s: float = 2.0) -> str:
  print(f"> {line}  (tcp {host}:{port})")
  sock = socket.create_connection((host, port), timeout=3.0)
  sock.settimeout(0.25)
  time.sleep(0.15)
  try:
    while True:
      try:
        chunk = sock.recv(4096)
      except socket.timeout:
        break
      if not chunk:
        break
  except OSError:
    pass
  sock.sendall((line + "\n").encode("ascii"))
  deadline = time.time() + timeout_s
  buf = b""
  while time.time() < deadline:
    try:
      chunk = sock.recv(4096)
    except socket.timeout:
      chunk = b""
    if chunk:
      buf += chunk
      while b"\n" in buf:
        raw, buf = buf.split(b"\n", 1)
        text = raw.decode("utf-8", errors="replace").strip()
        if text.startswith("OK ") or text.startswith("ERR "):
          print(f"< {text}")
          return text
    time.sleep(0.02)
  raise TimeoutError(f"no OK/ERR from WiFi console {host}")


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    "--port",
    default="uart2",
    choices=sorted(PORTS.keys()),
    help="Maix UART (default uart2 = B0/B1 /dev/ttyS2)",
  )
  parser.add_argument("--wifi-host", default="", help="ESP IP for TCP :2333 fallback")
  parser.add_argument("--wifi-port", type=int, default=2333)
  args = parser.parse_args()

  try:
    ser, cfg = _open_uart(args.port)
  except Exception as exc:
    print(f"FAIL open {args.port}: {exc}")
    return 1

  try:
    pong = _cmd_text(ser, "PING", cfg)
    scan = _cmd_text(ser, "SCAN", cfg)
    bat = _cmd_text(ser, "BAT", cfg)
    enc = _cmd_text(ser, "ENC", cfg)
    rsp_type, _ = _cmd_bin(ser, CMD_PING)
    if rsp_type != RSP_PONG:
      raise RuntimeError(f"binary PING got 0x{rsp_type:02X}, want 0x{RSP_PONG:02X}")
    telem_type, telem = _cmd_bin(ser, CMD_TELEM)
    if telem_type != RSP_TELEM or len(telem) < 42:
      raise RuntimeError(f"bad TELEM type=0x{telem_type:02X} len={len(telem)}")
    enc_fl, enc_fr = struct.unpack_from("<ii", telem, 0)
    bus_mv = struct.unpack_from("<H", telem, 16)[0]
    print(f"  telem enc={enc_fl}/{enc_fr} bus_mv={bus_mv}")
  except Exception as exc:
    print(f"FAIL UART ({cfg['device']}): {exc}")
    if not args.wifi_host:
      return 1
    try:
      pong = _cmd_wifi(args.wifi_host, args.wifi_port, "PING")
      scan = _cmd_wifi(args.wifi_host, args.wifi_port, "SCAN")
      bat = _cmd_wifi(args.wifi_host, args.wifi_port, "BAT")
      enc = _cmd_wifi(args.wifi_host, args.wifi_port, "ENC")
    except Exception as wifi_exc:
      print(f"FAIL WiFi: {wifi_exc}")
      return 1

  motor_ok = "motor=1" in scan
  print("---")
  print(f"port={args.port} device={cfg['device']} link={pong}")
  print(f"motors={scan}  {bat}  {enc}")
  if pong.startswith("OK ") and motor_ok:
    print("PASS")
    return 0
  if pong.startswith("OK "):
    print("PARTIAL: ESP answers but motors not ready")
    return 2
  print("FAIL")
  return 3


if __name__ == "__main__":
  raise SystemExit(main())
