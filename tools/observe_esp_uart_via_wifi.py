#!/usr/bin/env python3
"""Observe ESP TCP console while Maix sends an UART PING."""

from __future__ import annotations

import socket
import subprocess
import threading
import time


def main() -> int:
  """Run the remote UART2 probe while recording ESP console output."""
  sock = socket.create_connection(("192.168.20.148", 2333), timeout=3.0)
  sock.settimeout(0.2)
  lines: list[str] = []
  stop = threading.Event()

  def receive() -> None:
    buf = b""
    while not stop.is_set():
      try:
        chunk = sock.recv(4096)
      except socket.timeout:
        continue
      if not chunk:
        break
      buf += chunk
      while b"\n" in buf:
        raw, buf = buf.split(b"\n", 1)
        text = raw.decode("utf-8", errors="replace").strip()
        if text:
          lines.append(text)
          print(f"ESP TCP < {text}", flush=True)

  thread = threading.Thread(target=receive, daemon=True)
  thread.start()
  time.sleep(0.5)
  result = subprocess.run(
    [
      "ssh",
      "-o",
      "StrictHostKeyChecking=accept-new",
      "root@192.168.1.100",
      "python3 /tmp/probe_esp_uart_on_maix.py --port uart2",
    ],
    check=False,
    text=True,
  )
  time.sleep(0.5)
  stop.set()
  sock.close()
  thread.join(timeout=1.0)
  saw_pong = any(line == "OK PONG" for line in lines)
  print(f"ESP SAW UART PING: {'YES' if saw_pong else 'NO'}")
  return 0 if saw_pong else result.returncode or 1


if __name__ == "__main__":
  raise SystemExit(main())
