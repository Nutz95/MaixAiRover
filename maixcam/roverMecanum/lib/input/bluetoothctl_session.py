"""Long-lived bluetoothctl PTY so the BlueZ agent stays registered."""

import os
import select
import subprocess
import threading
import time

from lib.input.bluetoothctl_runner import BluetoothctlRunner


class BluetoothctlSession:
  """One bluetoothctl process for the whole app (agent NoInputNoOutput)."""

  def __init__(self) -> None:
    self._lock = threading.Lock()
    self._chunks = []
    self._master = None
    self._proc = None
    self._alive = False

  def start(self) -> None:
    """Power on, pairable, register agent; keep the process running."""
    if self._alive:
      return
    import pty

    master, slave = pty.openpty()
    self._proc = subprocess.Popen(
      ["bluetoothctl"],
      stdin=slave,
      stdout=slave,
      stderr=slave,
      close_fds=True,
    )
    os.close(slave)
    self._master = master
    self._alive = True
    threading.Thread(target=self._read_loop, daemon=True, name="btctl-pty").start()
    time.sleep(0.4)
    self.send("power on")
    self.send("pairable on")
    self.send("agent NoInputNoOutput")
    self.send("default-agent")
    time.sleep(0.4)
    print("bt: agent alive (NoInputNoOutput)")

  def close(self) -> None:
    """Quit bluetoothctl (app shutdown only — not DISC)."""
    if not self._alive:
      return
    self._alive = False
    try:
      self.send("quit")
    except OSError:
      pass
    if self._proc is not None:
      try:
        self._proc.wait(timeout=3)
      except subprocess.TimeoutExpired:
        self._proc.kill()
      self._proc = None
    if self._master is not None:
      try:
        os.close(self._master)
      except OSError:
        pass
      self._master = None

  def send(self, cmd: str) -> None:
    """Write one bluetoothctl command."""
    if self._master is None:
      raise OSError("bluetoothctl session is not started")
    print(f"  btctl: {cmd}")
    os.write(self._master, (cmd + "\n").encode())

  def pair(self, mac: str) -> str:
    """Force a fresh encrypted bond (PAIR button). Always remove first."""
    self.start()
    mac = mac.upper()
    print("bt: PAIR = remove old bond + encrypted re-pair (hold SYNC)")
    self._remove_bond(mac)
    time.sleep(2.0)

    pair_out = ""
    seen = ""
    for attempt in range(2):
      mark = self._mark()
      self.send("scan on")
      seen = self._wait_pairing_ready(mac, mark, 25.0)
      if not seen:
        self.send("scan off")
        print(f"bt: pair attempt {attempt + 1}/2 — not in SYNC mode")
        continue
      pair_mark = self._mark()
      # BlueZ 5.64 on MaixCAM must remain discovering while initiating LE pair.
      self.send(f"pair {mac}")
      pair_out = self._wait_since(
        pair_mark,
        ("Pairing successful", "Already paired", "Failed to pair"),
        25.0,
      )
      if BluetoothctlRunner.pair_succeeded(pair_out):
        break
      print(f"bt: pair attempt {attempt + 1}/2 failed")
      self.send("scan off")
      if attempt == 0:
        self._remove_device(mac)
        time.sleep(2.0)

    self.send("scan off")
    if not BluetoothctlRunner.pair_succeeded(pair_out):
      return seen + pair_out

    self.send(f"trust {mac}")
    time.sleep(0.5)
    return seen + pair_out + self.info(mac)

  def connect(self, mac: str) -> str:
    """Connect an already-paired pad and wait until GATT/HID is resolved."""
    self.start()
    mac = mac.upper()
    mark = self._mark()
    self.send(f"trust {mac}")
    self.send(f"connect {mac}")
    out = self._wait_since(
      mark,
      ("Connection successful", "Failed to connect", "Paired: no"),
      12.0,
    )
    if "Failed to connect" in out or "Paired: no" in out:
      self.send(f"info {mac}")
      time.sleep(0.4)
      return self._since(mark)
    self._wait_hid_ready(mac)
    return self._since(mark)

  def info(self, mac: str) -> str:
    """Run ``info MAC`` and return the new output."""
    self.start()
    mark = self._mark()
    self.send(f"info {mac}")
    time.sleep(0.5)
    return BluetoothctlRunner.strip_ansi(self._since(mark))

  def _remove_bond(self, mac: str) -> None:
    mark0 = self._mark()
    self.send(f"disconnect {mac}")
    self.send(f"remove {mac}")
    self._wait_since(
      mark0,
      ("Device has been removed", "not available", "Failed to disconnect"),
      8.0,
    )

  def _remove_device(self, mac: str) -> None:
    """Clear a failed temporary device object before the second pair attempt."""
    mark = self._mark()
    self.send(f"remove {mac}")
    self._wait_since(mark, ("Device has been removed", "not available"), 8.0)

  def _wait_pairing_ready(self, mac: str, mark: int, timeout_s: float) -> str:
    """Wait until Xbox is advertising for pairing (not a stale RSSI CHG)."""
    deadline = time.time() + timeout_s
    mac_u = mac.upper()
    while time.time() < deadline:
      chunk = BluetoothctlRunner.strip_ansi(self._since(mark))
      if BluetoothctlRunner.xbox_pairing_advertisement(chunk, mac_u):
        print(f"bt: pairing advert seen for {mac_u}")
        return chunk
      time.sleep(0.15)
    return ""

  def _wait_hid_ready(self, mac: str) -> None:
    """Wait for GATT/HID services to resolve."""
    mark = self._mark()
    self.send(f"info {mac}")
    self._wait_since(
      mark,
      ("ServicesResolved: yes", "00001812-", "Human Interface Device"),
      12.0,
    )

  def scan_for_device_name(self, name, timeout_sec=20.0, aliases=None) -> str:
    """Scan until an Xbox name match, then scan off. Empty string if none."""
    self.start()
    runner = BluetoothctlRunner()
    targets = runner._build_targets(name, aliases)
    print(
      f"  bt tip: hold Xbox SYNC until logo blinks fast"
      f" — scanning up to {timeout_sec:.0f}s for: {targets[0]!r}"
    )
    mark = self._mark()
    self.send("scan on")
    deadline = time.time() + max(3.0, float(timeout_sec))
    mac = ""
    while time.time() < deadline:
      chunk = self._since(mark)
      exact, partial, _seen = runner._match_scan_output(chunk, targets)
      mac = exact or partial or ""
      if mac:
        break
      time.sleep(0.2)
    self.send("scan off")
    time.sleep(0.2)
    return mac

  def _read_loop(self) -> None:
    while self._alive and self._master is not None:
      ready, _, _ = select.select([self._master], [], [], 0.3)
      if not ready:
        continue
      try:
        data = os.read(self._master, 8192)
      except OSError:
        break
      if not data:
        break
      text = data.decode("utf-8", errors="replace")
      with self._lock:
        self._chunks.append(text)
      stripped = BluetoothctlRunner.strip_ansi(text)
      if stripped.strip():
        print(stripped, end="" if stripped.endswith("\n") else "\n")

  def _mark(self) -> int:
    return len(self._snapshot())

  def _snapshot(self) -> str:
    with self._lock:
      return "".join(self._chunks)

  def _since(self, mark: int) -> str:
    return self._snapshot()[mark:]

  def _wait_since(self, mark: int, needles, timeout_s: float) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
      chunk = BluetoothctlRunner.strip_ansi(self._since(mark))
      for needle in needles:
        if needle in chunk:
          return chunk
      time.sleep(0.1)
    return BluetoothctlRunner.strip_ansi(self._since(mark))
