#!/usr/bin/env python3
"""Interactive TCP console to Waveshare ESP coordinator (WiFi).

Usage:
  python tools/wifi_console_client.py --host 192.168.20.148
  python tools/wifi_console_client.py --host 192.168.20.148 -c SCAN
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time


def recv_loop(sock: socket.socket, stop: threading.Event) -> None:
  buf = b""
  while not stop.is_set():
    try:
      sock.settimeout(0.3)
      chunk = sock.recv(4096)
    except socket.timeout:
      continue
    except OSError:
      break
    if not chunk:
      print("\n[disconnected]", flush=True)
      stop.set()
      break
    buf += chunk
    while b"\n" in buf:
      line, buf = buf.split(b"\n", 1)
      text = line.decode("utf-8", errors="replace").rstrip("\r")
      if text:
        print(f"< {text}", flush=True)


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--host", required=True, help="ESP IP (from Serial wifi: OK ip=...)")
  p.add_argument("--port", type=int, default=2333)
  p.add_argument("-c", "--cmd", action="append", default=[], help="one-shot command(s)")
  args = p.parse_args()

  sock = socket.create_connection((args.host, args.port), timeout=5.0)
  stop = threading.Event()
  t = threading.Thread(target=recv_loop, args=(sock, stop), daemon=True)
  t.start()
  time.sleep(0.2)

  for cmd in args.cmd:
    print(f"> {cmd}", flush=True)
    sock.sendall((cmd + "\n").encode("ascii"))
    time.sleep(0.4)

  if args.cmd:
    time.sleep(0.8)
    stop.set()
    sock.close()
    return 0

  print("REPL (Ctrl+C quit). Try: PING SCAN WIFI BAT", flush=True)
  try:
    while not stop.is_set():
      line = input("> ").strip()
      if not line:
        continue
      sock.sendall((line + "\n").encode("ascii"))
  except (EOFError, KeyboardInterrupt):
    print()
  stop.set()
  try:
    sock.close()
  except OSError:
    pass
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
