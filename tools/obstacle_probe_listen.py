"""Listen to MaixCAM obstacle probe TCP text stream (Windows-friendly).

Usage:
  python tools/obstacle_probe_listen.py 192.168.1.100
  python tools/obstacle_probe_listen.py 192.168.1.100 9400
"""

from __future__ import annotations

import socket
import sys


def main() -> int:
  """Connect and print probe lines until Ctrl+C."""
  host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
  port = int(sys.argv[2]) if len(sys.argv) > 2 else 9400
  print(f"connecting to {host}:{port} … (Ctrl+C to quit)")
  try:
    sock = socket.create_connection((host, port), timeout=5.0)
  except OSError as error:
    print(f"connect failed: {error}")
    print("Is the rover app running? Is Wi‑Fi on the same LAN?")
    return 1
  sock.settimeout(1.0)
  buffer = b""
  try:
    while True:
      try:
        chunk = sock.recv(4096)
      except socket.timeout:
        continue
      if not chunk:
        print("connection closed")
        return 0
      buffer += chunk
      while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        text = line.decode("utf-8", "replace").rstrip()
        if text:
          print(text, flush=True)
  except KeyboardInterrupt:
    print("\nbye")
    return 0
  finally:
    sock.close()


if __name__ == "__main__":
  raise SystemExit(main())
