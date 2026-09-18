#!/usr/bin/env python3
"""Encrypted Xbox LE pair via interactive bluetoothctl agent (PTY)."""

import os
import pty
import re
import select
import subprocess
import sys
import time

MAC = sys.argv[1] if len(sys.argv) > 1 else "78:86:2E:AC:8D:03"
SCAN_TIMEOUT_S = float(sys.argv[2]) if len(sys.argv) > 2 else 75.0


def drain(master, seconds=1.0):
  end = time.time() + seconds
  chunks = []
  while time.time() < end:
    ready, _, _ = select.select([master], [], [], 0.2)
    if not ready:
      continue
    try:
      data = os.read(master, 8192)
    except OSError:
      break
    if not data:
      break
    chunks.append(data)
  text = b"".join(chunks).decode("utf-8", errors="replace")
  if text.strip():
    sys.stdout.write(text)
    if not text.endswith("\n"):
      sys.stdout.write("\n")
    sys.stdout.flush()
  return text


def send(master, cmd, wait=1.0):
  print(f">>> {cmd}", flush=True)
  os.write(master, (cmd + "\n").encode())
  return drain(master, wait)


def mac_seen(text, mac):
  # bluetoothctl prints MAC with colons; strip ANSI/control chars first.
  clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]|\x01|\x02", "", text)
  return mac.upper() in clean.upper()


def wait_for_mac(master, mac, timeout_s):
  print(
    f"=== SCAN up to {int(timeout_s)}s — hold Xbox SYNC until pair starts ===",
    flush=True,
  )
  deadline = time.time() + timeout_s
  buf = ""
  while time.time() < deadline:
    chunk = drain(master, 1.0)
    buf += chunk
    if mac_seen(buf, mac) or mac_seen(chunk, mac):
      print(f"=== FOUND {mac} — pairing now (scan still on) ===", flush=True)
      return True
    remaining = int(deadline - time.time())
    if remaining % 10 == 0:
      print(f"... still scanning ({remaining}s left)", flush=True)
  return False


def main():
  print(f"=== target {MAC} ===", flush=True)
  subprocess.run(["bluetoothctl", "disconnect", MAC], capture_output=True)
  subprocess.run(["bluetoothctl", "remove", MAC], capture_output=True)
  time.sleep(0.8)

  master, slave = pty.openpty()
  proc = subprocess.Popen(
    ["bluetoothctl"],
    stdin=slave,
    stdout=slave,
    stderr=slave,
    close_fds=True,
  )
  os.close(slave)
  time.sleep(0.4)
  drain(master, 0.8)

  send(master, "power on", 1.0)
  send(master, "pairable on", 0.5)
  send(master, "discoverable on", 0.5)
  # Just Works encrypted bond (required for HOG / joystick).
  send(master, "agent NoInputNoOutput", 1.0)
  send(master, "default-agent", 1.0)
  send(master, "scan on", 0.8)

  found = wait_for_mac(master, MAC, SCAN_TIMEOUT_S)
  if not found:
    print(f"FAIL: {MAC} not seen in scan — re-press Xbox SYNC and retry", flush=True)
    send(master, "scan off", 1.0)
    send(master, "quit", 1.0)
    try:
      proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
      proc.kill()
    sys.exit(2)

  # Pair while advertising window is open; keep scan on during bond.
  pair_out = send(master, f"pair {MAC}", 45.0)
  send(master, f"trust {MAC}", 2.0)
  send(master, "scan off", 1.0)
  send(master, f"connect {MAC}", 25.0)
  info_out = send(master, f"info {MAC}", 2.5)
  send(master, "quit", 1.0)
  try:
    proc.wait(timeout=5)
  except subprocess.TimeoutExpired:
    proc.kill()

  print("=== INPUT NODES ===", flush=True)
  subprocess.run(
    [
      "bash",
      "-lc",
      "ls -l /dev/input/event*; echo; "
      "cat /proc/bus/input/devices | grep -A14 -iE 'xbox|microsoft' || echo NO_XBOX_INPUT",
    ]
  )
  print("=== JOURNAL HOG (last boot window) ===", flush=True)
  subprocess.run(
    [
      "bash",
      "-lc",
      "journalctl -u bluetooth --no-pager -n 80 | "
      "grep -iE 'hog|hid|pair|encrypt|bond|xbox|78:86|Successful' | tail -40 || true",
    ]
  )

  paired = "Paired: yes" in info_out
  connected = "Connected: yes" in info_out
  ok_pair = "Pairing successful" in pair_out or "Already paired" in pair_out or paired
  print(
    f"=== RESULT paired={paired} connected={connected} pair_ok={ok_pair} ===",
    flush=True,
  )
  if not ok_pair:
    sys.exit(3)


if __name__ == "__main__":
  main()
