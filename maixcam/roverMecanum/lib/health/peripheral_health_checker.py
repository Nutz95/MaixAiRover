"""Build a peripheral checklist after the Xbox pad connects."""

from __future__ import annotations

import time

from lib.motion.drive_backend_kind import DriveBackendKind
from lib.esp.esp_uart_client import EspUartClient
from lib.esp.esp_usb_client import EspUsbClient
from lib.esp.esp_wifi_client import EspWifiClient
from lib.health.peripheral_check import PeripheralCheck
from lib.health.peripheral_checklist import PeripheralChecklist


class PeripheralHealthChecker:
  """Probe Xbox, camera, and either Yahboom USB or ESP link."""

  def __init__(
    self,
    esp_wifi_host: str = "",
    esp_wifi_port: int = 2333,
    esp_uart_port: str = "uart4",
    rear_uart_port: str = "",
    drive_backend: DriveBackendKind = DriveBackendKind.ESP,
  ) -> None:
    self._esp_wifi_host = (esp_wifi_host or "").strip()
    self._esp_wifi_port = int(esp_wifi_port)
    self._esp_uart_port = (esp_uart_port or "uart4").strip()
    self._rear_uart_port = (rear_uart_port or "").strip()
    self._drive_backend = drive_backend
    self._uart_error = ""
    self._usb_error = ""

  def run(
    self,
    *,
    xbox_connected: bool,
    camera_ok: bool,
    motion_is_stub: bool = True,
    yahboom_board=None,
  ) -> PeripheralChecklist:
    """Run checks and return an immutable checklist."""
    del motion_is_stub
    checks = [
      PeripheralCheck(
        name="Xbox",
        ok=xbox_connected,
        detail="HID connected" if xbox_connected else "not connected",
      ),
      PeripheralCheck(
        name="Camera",
        ok=camera_ok,
        detail="preview up" if camera_ok else "disabled or failed",
      ),
    ]
    if self._drive_backend is DriveBackendKind.YAHBOOM:
      checks.extend(self._probe_yahboom(yahboom_board))
    else:
      checks.extend(self._probe_esp())
      checks.extend(self._probe_rear_uart())
    return PeripheralChecklist(checks=checks)

  def _probe_yahboom(self, board) -> list[PeripheralCheck]:
    """Battery / IMU / encoders from the open Yahboom drive board."""
    if board is None:
      return [
        PeripheralCheck(name="Yahboom USB", ok=False, detail="board not opened"),
        PeripheralCheck(name="Battery", ok=False, detail="skipped"),
        PeripheralCheck(name="IMU", ok=False, detail="skipped"),
        PeripheralCheck(name="Encoders", ok=False, detail="skipped"),
      ]
    for _ in range(12):
      board.poll()
      time.sleep(0.04)
    bat = board.battery()
    imu = board.imu_attitude()
    enc = board.read_encoders()
    link_ok = bat is not None or imu is not None
    bat_ok = bat is not None and bat.volts >= 6.0
    imu_ok = imu is not None
    enc_ok = board.has_encoder_report()
    bat_detail = "no report" if bat is None else f"{bat.volts:.1f} V"
    imu_detail = "no report" if imu is None else (
      f"y={imu.yaw_deg:.0f} p={imu.pitch_deg:.0f} r={imu.roll_deg:.0f}"
    )
    enc_detail = (
      "no report"
      if not enc_ok
      else f"FL={enc.m1} FR={enc.m2} RL={enc.m3} RR={enc.m4}"
    )
    return [
      PeripheralCheck(
        name="Yahboom USB",
        ok=link_ok,
        detail="auto-report OK" if link_ok else "no telemetry yet",
      ),
      PeripheralCheck(name="Battery", ok=bat_ok, detail=bat_detail[:48]),
      PeripheralCheck(name="IMU", ok=imu_ok, detail=imu_detail[:48]),
      PeripheralCheck(name="Encoders", ok=enc_ok, detail=enc_detail[:48]),
    ]

  def _probe_esp(self):
    """Prefer UART4 (aux header), then USB CP210x, then WiFi console."""
    self._uart_error = ""
    self._usb_error = ""
    uart_checks = self._probe_via_uart()
    if uart_checks is not None:
      return uart_checks
    usb_checks = self._probe_via_usb()
    if usb_checks is not None:
      return usb_checks
    if self._esp_wifi_host:
      return self._probe_via_wifi()
    uart_detail = self._uart_error or "timeout — TX→P_TX, RX→P_RX, GND"
    usb_detail = self._usb_error or "CP210x missing (Maix USB=Host + cable)"
    return [
      PeripheralCheck(name="ESP UART", ok=False, detail=uart_detail[:48]),
      PeripheralCheck(name="ESP USB", ok=False, detail=usb_detail[:48]),
      PeripheralCheck(name="Motors", ok=False, detail="skipped (no ESP link)"),
    ]

  def _probe_via_uart(self):
    client = EspUartClient.from_port(self._esp_uart_port)
    try:
      client.open()
      pong = client.command("PING", timeout_s=2.0)
      scan = client.command("SCAN", timeout_s=2.0)
    except Exception as exc:
      self._uart_error = str(exc)
      print(f"checklist ESP UART: {exc}")
      try:
        client.close()
      except Exception:
        pass
      return None
    try:
      bat = client.command("BAT", timeout_s=2.0)
    except Exception as exc:
      bat = f"ERR BAT {exc}"
    client.close()
    return self._esp_checks(link_name="ESP UART", pong=pong, scan=scan, bat=bat)

  def _probe_via_usb(self):
    client = EspUsbClient()
    try:
      client.open()
      pong = client.command("PING", timeout_s=2.0)
      scan = client.command("SCAN", timeout_s=2.0)
    except Exception as exc:
      self._usb_error = str(exc)
      print(f"checklist ESP USB: {exc}")
      try:
        client.close()
      except Exception:
        pass
      return None
    try:
      bat = client.command("BAT", timeout_s=2.0)
    except Exception as exc:
      bat = f"ERR BAT {exc}"
    client.close()
    checks = [
      PeripheralCheck(
        name="ESP UART",
        ok=False,
        detail=(self._uart_error or "timeout — using USB CP210x")[:48],
      ),
    ]
    checks.extend(
      self._esp_checks(link_name="ESP USB", pong=pong, scan=scan, bat=bat)
    )
    return checks

  def _probe_via_wifi(self):
    client = EspWifiClient(self._esp_wifi_host, self._esp_wifi_port)
    try:
      client.open()
      pong = client.command("PING")
      scan = client.command("SCAN")
      try:
        bat = client.command("BAT")
      except Exception as exc:
        bat = f"ERR BAT {exc}"
    except Exception as exc:
      return [
        PeripheralCheck(
          name="ESP UART",
          ok=False,
          detail=(self._uart_error or "timeout — TX→P_TX / RX→P_RX")[:48],
        ),
        PeripheralCheck(
          name="ESP USB",
          ok=False,
          detail=(self._usb_error or "CP210x unavailable")[:48],
        ),
        PeripheralCheck(
          name="ESP WiFi",
          ok=False,
          detail=f"{self._esp_wifi_host}: {exc}"[:48],
        ),
        PeripheralCheck(name="Motors", ok=False, detail="skipped (no ESP link)"),
      ]
    finally:
      client.close()
    checks = [
      PeripheralCheck(name="ESP UART", ok=False, detail="timeout — WiFi fallback"),
      PeripheralCheck(name="ESP USB", ok=False, detail="skipped"),
    ]
    checks.extend(
      self._esp_checks(link_name="ESP WiFi", pong=pong, scan=scan, bat=bat)
    )
    return checks

  def _esp_checks(self, *, link_name: str, pong: str, scan: str, bat: str):
    link_ok = pong.startswith("OK ")
    motor_ok = "motor=1" in scan
    bat_ok = bat.startswith("OK BAT") or "unsupported" in bat or "no INA" in bat
    motor_detail = scan
    if not motor_ok:
      motor_detail = f"{scan} (front TB6612 not ready?)"
    return [
      PeripheralCheck(name=link_name, ok=link_ok, detail=pong),
      PeripheralCheck(name="Motors", ok=motor_ok, detail=motor_detail),
      PeripheralCheck(name="Battery", ok=bat_ok, detail=bat),
    ]

  def _probe_rear_uart(self):
    """Optional quick PING on the rear board UART (does not replace front checks)."""
    if not self._rear_uart_port:
      return []
    client = EspUartClient.from_port(self._rear_uart_port)
    try:
      client.open()
      pong = client.command("PING", timeout_s=2.0)
      client.close()
      ok = pong.startswith("OK ")
      return [PeripheralCheck(name="ESP rear UART", ok=ok, detail=pong[:48])]
    except Exception as exc:
      print(f"checklist ESP rear UART: {exc}")
      try:
        client.close()
      except Exception:
        pass
      return [
        PeripheralCheck(
          name="ESP rear UART",
          ok=False,
          detail=str(exc)[:48],
        )
      ]
