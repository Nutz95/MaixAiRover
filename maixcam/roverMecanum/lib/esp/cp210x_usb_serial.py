"""Userspace CP210x UART via libusb (no kernel usbserial/cp210x module).

MaixCAM2 stock kernel has ``# CONFIG_USB_SERIAL is not set``, so the Waveshare
CP2102 never becomes ``/dev/ttyUSB0``. This class talks to the chip directly
when the Maix USB port is in **host** mode and the ESP is plugged in.
"""

from __future__ import annotations

import ctypes
import struct
import time
from ctypes import POINTER, byref, c_int, c_ubyte, c_uint16, c_void_p

# Silabs CP210x vendor requests (host → interface).
_CP210X_IFC_ENABLE = 0x00
_CP210X_SET_LINE_CTL = 0x03
_CP210X_SET_MHS = 0x07
_CP210X_SET_BAUDRATE = 0x1E
_UART_ENABLE = 0x0001
_LINE_CTL_8N1 = 0x0800
_REQ_HOST_TO_IFACE = 0x41
_VID = 0x10C4
_PID = 0xEA60
# CP2102N on Waveshare: bulk EP2 (not EP1).
_EP_OUT = 0x02
_EP_IN = 0x82

_LIB = None


def _libusb():
  """Load libusb on first open (host tests import this module without .so)."""
  global _LIB
  if _LIB is not None:
    return _LIB
  lib = ctypes.CDLL("libusb-1.0.so.0")
  lib.libusb_init.argtypes = [POINTER(c_void_p)]
  lib.libusb_init.restype = c_int
  lib.libusb_exit.argtypes = [c_void_p]
  lib.libusb_open_device_with_vid_pid.argtypes = [c_void_p, c_uint16, c_uint16]
  lib.libusb_open_device_with_vid_pid.restype = c_void_p
  lib.libusb_close.argtypes = [c_void_p]
  lib.libusb_claim_interface.argtypes = [c_void_p, c_int]
  lib.libusb_claim_interface.restype = c_int
  lib.libusb_release_interface.argtypes = [c_void_p, c_int]
  lib.libusb_set_configuration.argtypes = [c_void_p, c_int]
  lib.libusb_set_configuration.restype = c_int
  lib.libusb_control_transfer.argtypes = [
    c_void_p, c_ubyte, c_ubyte, c_uint16, c_uint16, POINTER(c_ubyte), c_uint16, c_uint16,
  ]
  lib.libusb_control_transfer.restype = c_int
  lib.libusb_bulk_transfer.argtypes = [
    c_void_p, c_ubyte, POINTER(c_ubyte), c_int, POINTER(c_int), c_uint16,
  ]
  lib.libusb_bulk_transfer.restype = c_int
  _LIB = lib
  return lib


class Cp210xUsbSerial:
  """Minimal CP210x UART port over libusb (115200 8N1 by default)."""

  def __init__(self, baud: int = 115200, timeout_ms: int = 200) -> None:
    self._baud = int(baud)
    self._timeout_ms = int(timeout_ms)
    self._ctx = c_void_p()
    self._handle = c_void_p()
    self._claimed = False

  def open(self) -> None:
    """Find CP210x (10c4:ea60), claim interface 0, enable UART at configured baud."""
    lib = _libusb()
    if lib.libusb_init(byref(self._ctx)) != 0:
      raise RuntimeError("libusb_init failed")
    self._handle = lib.libusb_open_device_with_vid_pid(self._ctx, _VID, _PID)
    if not self._handle:
      lib.libusb_exit(self._ctx)
      self._ctx = c_void_p()
      raise RuntimeError("CP210x 10c4:ea60 not found (USB host + cable?)")
    lib.libusb_set_configuration(self._handle, 1)
    if lib.libusb_claim_interface(self._handle, 0) != 0:
      self.close()
      raise RuntimeError("libusb_claim_interface(0) failed")
    self._claimed = True
    self._ctrl(_CP210X_IFC_ENABLE, _UART_ENABLE)
    self._set_baud(self._baud)
    self._ctrl(_CP210X_SET_LINE_CTL, _LINE_CTL_8N1)
    self._ctrl(_CP210X_SET_MHS, 0x0000)

  def close(self) -> None:
    """Release interface and close the USB device."""
    lib = _LIB
    if lib is None:
      return
    if self._handle and self._claimed:
      try:
        self._ctrl(_CP210X_IFC_ENABLE, 0)
      except Exception as swallowed:
        print(f"cp210x_usb_serial.py: {swallowed}")
      lib.libusb_release_interface(self._handle, 0)
      self._claimed = False
    if self._handle:
      lib.libusb_close(self._handle)
      self._handle = c_void_p()
    if self._ctx:
      lib.libusb_exit(self._ctx)
      self._ctx = c_void_p()

  def write(self, data: bytes) -> int:
    """Write bytes to the UART bulk OUT endpoint."""
    if not data:
      return 0
    lib = _libusb()
    buf = (c_ubyte * len(data)).from_buffer_copy(data)
    transferred = c_int(0)
    rc = lib.libusb_bulk_transfer(
      self._handle, _EP_OUT, buf, len(data), byref(transferred), self._timeout_ms,
    )
    if rc != 0 and transferred.value == 0:
      raise RuntimeError(f"bulk OUT failed rc={rc}")
    return transferred.value

  def write_str(self, text: str) -> int:
    """Write a UTF-8 / ASCII string."""
    return self.write(text.encode("ascii", errors="ignore"))

  def read(self, max_len: int = 256, timeout_ms: int | None = None) -> bytes:
    """Read up to ``max_len`` bytes from bulk IN (empty on timeout)."""
    lib = _libusb()
    timeout = self._timeout_ms if timeout_ms is None else int(timeout_ms)
    buf = (c_ubyte * max_len)()
    transferred = c_int(0)
    rc = lib.libusb_bulk_transfer(
      self._handle, _EP_IN, buf, max_len, byref(transferred), timeout,
    )
    # LIBUSB_ERROR_TIMEOUT == -7
    if rc == -7:
      return b""
    if rc != 0 and transferred.value == 0:
      return b""
    return bytes(buf[: transferred.value])

  def _ctrl(self, request: int, value: int, data: bytes = b"") -> None:
    lib = _libusb()
    length = len(data)
    buf = (c_ubyte * length).from_buffer_copy(data) if length else POINTER(c_ubyte)()
    rc = lib.libusb_control_transfer(
      self._handle,
      _REQ_HOST_TO_IFACE,
      request,
      value,
      0,
      buf,
      length,
      self._timeout_ms,
    )
    if rc < 0:
      raise RuntimeError(f"CP210x ctrl req=0x{request:02x} val=0x{value:04x} rc={rc}")

  def _set_baud(self, baud: int) -> None:
    payload = struct.pack("<I", int(baud))
    self._ctrl(_CP210X_SET_BAUDRATE, 0, payload)


def _self_check() -> None:
  """ponytail: opens device if present; skips cleanly when unplugged."""
  port = Cp210xUsbSerial(115200)
  try:
    port.open()
  except RuntimeError as exc:
    if "not found" in str(exc):
      print("cp210x_usb_serial: skip (device absent)")
      return
    raise
  try:
    port.write_str("PING\n")
    time.sleep(0.2)
    raw = port.read(128, timeout_ms=500)
    print(f"cp210x_usb_serial: wrote PING, rx={raw!r}")
  finally:
    port.close()


if __name__ == "__main__":
  _self_check()
