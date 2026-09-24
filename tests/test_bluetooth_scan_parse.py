"""Unit tests for bluetoothctl scan line parsing."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.input.bluetoothctl_runner import BluetoothctlRunner


SAMPLE = """
Discovery started
[CHG] Controller 38:7A:CC:98:34:39 Discovering: yes
[NEW] Device 28:E6:A9:4D:63:53 49" Odyssey OLED G9
[NEW] Device 78:86:2E:AC:8D:03 Xbox Wireless Controller
[CHG] Device 78:86:2E:AC:8D:03 TxPower: 20
[CHG] Device 78:86:2E:AC:8D:03 UUIDs: 00001812-0000-1000-8000-00805f9b34fb
"""


def test_parse_new_device_line_with_name():
  runner = BluetoothctlRunner()
  mac, name = runner._parse_device_line(
    "[NEW] Device 78:86:2E:AC:8D:03 Xbox Wireless Controller"
  )
  assert mac == "78:86:2E:AC:8D:03"
  assert name == "Xbox Wireless Controller"


def test_last_connected_flag_ignores_transient_yes():
  runner = BluetoothctlRunner()
  output = """
[CHG] Device 78:86:2E:AC:8D:03 Connected: yes
Failed to connect: org.bluez.Error.Failed le-connection-abort-by-local
Device 78:86:2E:AC:8D:03 (public)
	Paired: yes
	Connected: no
"""
  assert runner.last_flag_yes(output, "Connected") is False
  assert runner.last_flag_yes(output, "Paired") is True


def test_pair_succeeded_false_when_failed_even_if_paired_yes():
  output = """
Failed to pair: org.bluez.Error.ConnectionAttemptFailed
	Paired: yes
	Connected: no
"""
  assert BluetoothctlRunner.pair_succeeded(output) is False


def test_pair_succeeded_true_on_pairing_successful():
  output = """
Attempting to pair with 78:86:2E:AC:8D:03
Pairing successful
	Paired: yes
"""
  assert BluetoothctlRunner.pair_succeeded(output) is True


def test_bond_ready_requires_paired_and_connected():
  output = """
	Paired: yes
	Connected: yes
"""
  assert BluetoothctlRunner.bond_ready(output) is True
  assert BluetoothctlRunner.bond_ready("\tPaired: yes\n\tConnected: no\n") is False
  runner = BluetoothctlRunner()
  match = runner._match_scan_output(SAMPLE, ["xbox wireless controller"])
  assert match.exact_mac == "78:86:2E:AC:8D:03"
  assert match.devices_seen >= 2
  assert match.partial_mac is None or match.partial_mac == match.exact_mac


def test_pairing_adv_requires_manufacturer_or_new_xbox():
  mac = "78:86:2E:AC:8D:03"
  rssi_only = f"[CHG] Device {mac} RSSI: -45\n"
  assert BluetoothctlRunner.xbox_pairing_advertisement(rssi_only, mac) is False
  pairing = (
    f"[CHG] Device {mac} ManufacturerData Key: 0x0006\n"
    f"[CHG] Device {mac} ManufacturerData Value:\n"
    "  03 00 80                                         ...\n"
  )
  assert BluetoothctlRunner.xbox_pairing_advertisement(pairing, mac) is True
  fresh = f"[NEW] Device {mac} Xbox Wireless Controller\n"
  assert BluetoothctlRunner.xbox_pairing_advertisement(fresh, mac) is True

