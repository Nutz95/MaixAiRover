"""Pairing by controller name; MAC stored in config.json."""

from lib.input.bluetooth_command_result import BluetoothCommandResult
from lib.input.bluetoothctl_runner import BluetoothctlRunner
from lib.input.bluetoothctl_session import BluetoothctlSession
from lib.input.controller_scan_result import ControllerScanResult


class BluetoothPairingService:
  """Pairing by controller name; MAC stored in config.json."""

  def __init__(self, config_store) -> None:
    self._config_store = config_store
    self._session = BluetoothctlSession()

  def ensure_agent(self) -> None:
    """Start the long-lived BlueZ agent (Xbox can reconnect by itself)."""
    try:
      self._session.start()
    except Exception as exc:
      print(f"bt: agent start failed: {exc}")

  def close(self) -> None:
    """Stop the bluetoothctl agent (app exit only)."""
    self._session.close()

  def connect_saved(self) -> BluetoothCommandResult:
    """Reconnect to the MAC already stored in config."""
    mac = self._saved_mac()
    if not mac:
      return BluetoothCommandResult(error="No saved controller — use PAIR first")
    output = self._session.connect(mac)
    if BluetoothctlRunner().last_flag_yes(output, "Connected"):
      return BluetoothCommandResult(output=output)
    if "Paired: no" in output:
      return BluetoothCommandResult(output=output, error="Not paired — use PAIR + hold SYNC")
    if "Failed to connect" in output:
      return BluetoothCommandResult(
        output=output,
        error="CONNECT aborted — PAIR + hold SYNC, forget pad on PC",
      )
    return BluetoothCommandResult(output=output, error="CONNECT failed — try PAIR")

  def scan_for_controller(self) -> ControllerScanResult:
    """Use saved MAC, or scan until the Xbox name appears."""
    saved = self._saved_mac()
    if saved:
      print(f"pairing: using saved MAC {saved} (hold SYNC)")
      return ControllerScanResult(mac=saved)
    config = self._config_store.get()
    name = config.get("controller_name", "Xbox Wireless Controller")
    aliases = config.get("controller_name_aliases", [])
    timeout_sec = float(config.get("bluetooth_scan_timeout_sec", 20))
    print(f"pairing: scan for '{name}' (up to {timeout_sec:.0f}s)...")
    mac = self._session.scan_for_device_name(name, timeout_sec=timeout_sec, aliases=aliases)
    if not mac:
      return ControllerScanResult(
        error="Controller not found — hold SYNC (logo blinks), then PAIR again"
      )
    self._config_store.set_controller_mac(mac)
    print(f"pairing: MAC saved {mac}")
    return ControllerScanResult(mac=mac)

  def pair_mac(self, mac: str) -> BluetoothCommandResult:
    """Encrypted pair with the live agent; Xbox should then stay / reconnect."""
    output = self._session.pair(mac)
    if BluetoothctlRunner.pair_succeeded(output) or BluetoothctlRunner.bond_ready(output):
      self._config_store.set_controller_mac(mac)
      return BluetoothCommandResult(output=output)
    if "not available" in output.lower():
      return BluetoothCommandResult(
        output=output,
        error="Controller not seen — hold Xbox SYNC, retry PAIR",
      )
    return BluetoothCommandResult(
      output=output,
      error="Pairing failed — hold SYNC, forget pad on PC, retry PAIR",
    )

  def _saved_mac(self) -> str:
    config = self._config_store.get()
    return (config.get("controller_mac") or "").strip().upper()
