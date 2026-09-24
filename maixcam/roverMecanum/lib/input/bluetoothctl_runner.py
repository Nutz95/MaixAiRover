"""Parse bluetoothctl output (scan lines, pair/connect success)."""

import re


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x01|\x02")


class BluetoothctlRunner:
  """Helpers for bluetoothctl text. Live agent lives in BluetoothctlSession."""

  _MAC_RE = re.compile(r"([0-9A-F]{2}(?::[0-9A-F]{2}){5})", re.IGNORECASE)
  XBOX_NAME_ALIASES = (
    "xbox wireless controller",
    "xbox series x controller",
    "xbox series s controller",
    "xbox adaptive controller",
    "xbox one wireless controller",
    "microsoft xbox",
  )
  _DEVICE_LINE_RE = re.compile(
    r"(?:\[(?:NEW|CHG|DEL)\]\s+)?Device\s+"
    r"([0-9A-F]{2}(?::[0-9A-F]{2}){5})\s+(.+)$",
    re.IGNORECASE,
  )

  def last_flag_yes(self, output: str, key: str) -> bool:
    """Return True if the last ``Key: yes/no`` line in bluetoothctl output is yes."""
    needle = key.lower() + ":"
    last = None
    for line in self.strip_ansi(output).splitlines():
      low = line.strip().lower()
      if needle not in low:
        continue
      last = "yes" in low.split(needle, 1)[-1]
    return bool(last)

  @staticmethod
  def pair_succeeded(output: str) -> bool:
    """True only if pairing succeeded after the last failure, if any."""
    text = BluetoothctlRunner.strip_ansi(output)
    ok_pos = max(text.rfind("Pairing successful"), text.rfind("Already paired"))
    fail_pos = text.rfind("Failed to pair")
    if ok_pos < 0 and fail_pos < 0:
      return BluetoothctlRunner().last_flag_yes(text, "Paired")
    return ok_pos > fail_pos

  @staticmethod
  def bond_ready(output: str) -> bool:
    """True if the pad is paired and connected (reuse bond, not a fresh pair)."""
    runner = BluetoothctlRunner()
    return runner.last_flag_yes(output, "Paired") and runner.last_flag_yes(output, "Connected")

  @staticmethod
  def xbox_pairing_advertisement(output: str, mac: str) -> bool:
    """
    True when the pad is advertising for pairing.

    Xbox BLE pairing manufacturer data is ``03 00 80``. A bare
    ``[CHG] Device MAC RSSI`` is not enough — that fires on stale cache.
    A fresh ``[NEW] Device MAC Xbox…`` also counts.
    """
    text = BluetoothctlRunner.strip_ansi(output)
    mac_u = (mac or "").upper()
    if not mac_u or mac_u not in text.upper():
      return False
    if "03 00 80" in text:
      return True
    for line in text.splitlines():
      low = line.strip().lower()
      if "[new] device" in low and mac_u.lower() in low and "xbox" in low:
        return True
    return False

  @staticmethod
  def strip_ansi(text: str) -> str:
    """Strip bluetoothctl color/control sequences."""
    return _ANSI_RE.sub("", text or "")

  def _build_targets(self, name, aliases):
    target = (name or "").lower().strip()
    targets = [target] if target else []
    if aliases:
      for alias in aliases:
        if isinstance(alias, str) and alias.strip():
          low = alias.lower().strip()
          if low not in targets:
            targets.append(low)
    for alias in self.XBOX_NAME_ALIASES:
      if alias not in targets:
        targets.append(alias)
    return targets or ["xbox wireless controller"]

  def _match_scan_output(self, output, targets):
    """Parse bluetoothctl device listings; return (exact_mac, partial_mac, seen)."""
    exact = None
    partial = None
    seen = 0
    for line in output.splitlines():
      parsed = self._parse_device_line(line.strip())
      if parsed is None:
        continue
      mac, device_name = parsed
      if not device_name or device_name.startswith("("):
        continue
      upper = device_name.upper()
      if upper.startswith(("RSSI:", "TXPOWER:", "UUIDS:", "MANUFACTURERDATA", "SERVICEDATA")):
        continue
      seen += 1
      print(f"  bt scan: {mac} {device_name}")
      dn = device_name.lower()
      for candidate in targets:
        if dn == candidate:
          exact = mac
          break
        if candidate in dn or ("xbox" in dn and "controller" in dn):
          partial = partial or mac
      if exact:
        break
    return exact, partial, seen

  def _parse_device_line(self, line):
    """Extract MAC + name from a bluetoothctl device line, or None."""
    if not line:
      return None
    name_match = re.search(r"Name:\s*(.+)$", line, re.IGNORECASE)
    mac_match = self._MAC_RE.search(line)
    if name_match and mac_match:
      return mac_match.group(1).upper(), name_match.group(1).strip()
    device_match = self._DEVICE_LINE_RE.match(line)
    if device_match:
      mac = device_match.group(1).upper()
      tail = device_match.group(2).strip()
      if tail.lower().startswith("name:"):
        tail = tail.split(":", 1)[-1].strip()
      return mac, tail
    return None
