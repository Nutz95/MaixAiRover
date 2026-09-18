import subprocess


class BluetoothInstaller:
  """Enable Bluetooth on MaixCam2 (BlueZ via bluetoothctl)."""

  def install(self):
    """Apply the old-kernel Xbox workaround, then enable BlueZ."""
    results = []
    results.append(self._disable_ertm())
    results.append(self._run_shell("bluetoothctl power on"))
    results.append(self._run_shell("bluetoothctl pairable on"))
    self._ensure_rc_local()
    return "\n".join(results)

  def _disable_ertm(self):
    path = "/sys/module/bluetooth/parameters/disable_ertm"
    try:
      with open(path, "w", encoding="utf-8") as handle:
        handle.write("Y\n")
      return "bluetooth: ERTM disabled (Xbox/kernel 4.19 workaround)"
    except OSError as exc:
      return f"bluetooth: ERTM workaround unavailable ({exc})"

  def _ensure_rc_local(self):
    marker = "bluetoothctl power on"
    try:
      with open("/etc/rc.local", "r") as f:
        content = f.read()
      if marker in content:
        return "rc.local: deja configure"
      with open("/etc/rc.local", "a") as f:
        f.write(f'\necho "{marker}" | bluetoothctl\n')
      return "rc.local: bluetoothctl power on ajoute"
    except OSError as exc:
      return f"rc.local: skip ({exc})"

  def _run_shell(self, command):
    proc = subprocess.run(
      command,
      shell=True,
      capture_output=True,
      text=True,
      timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return out.strip() or f"OK: {command}"
