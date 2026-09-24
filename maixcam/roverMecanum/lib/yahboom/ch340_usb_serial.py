"""Userspace CH340 UART via libusb (MaixCAM2 has no CONFIG_USB_SERIAL).

Yahboom ROS board Micro-USB is QinHeng CH340 (VID ``1a86`` PID ``7523``).
Same pattern as ``Cp210xUsbSerial``: talk to the chip over USB host without
``/dev/ttyUSB*``.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import POINTER, byref, c_int, c_ubyte, c_uint16, c_void_p

_VID = 0x1A86
_PID = 0x7523
_EP_OUT = 0x02
_EP_IN = 0x82
_REQ_VENDOR_WRITE = 0x40
_REQ_VENDOR_READ = 0xC0
_REQ_SERIAL_INIT = 0xA1
_REQ_WRITE_REG = 0x9A
_REQ_MODEM_CTRL = 0xA4
_BAUDBASE = 1532620800

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


class Ch340UsbSerial:
  """Minimal CH340 UART port over libusb (default 115200 8N1)."""

  def __init__(self, baud: int = 115200, timeout_ms: int = 8) -> None:
    self._baud = int(baud)
    self._timeout_ms = int(timeout_ms)
    self._ctx = c_void_p()
    self._handle = c_void_p()
    self._claimed = False

  def open(self) -> None:
    """Find CH340 (1a86:7523), claim iface 0, configure baud."""
    lib = _libusb()
    if lib.libusb_init(byref(self._ctx)) != 0:
      raise RuntimeError("libusb_init failed")
    self._handle = lib.libusb_open_device_with_vid_pid(self._ctx, _VID, _PID)
    if not self._handle:
      lib.libusb_exit(self._ctx)
      self._ctx = c_void_p()
      raise RuntimeError("CH340 1a86:7523 not found (USB host + Yahboom Micro-USB?)")
    lib.libusb_set_configuration(self._handle, 1)
    if lib.libusb_claim_interface(self._handle, 0) != 0:
      self.close()
      raise RuntimeError("libusb_claim_interface(0) failed for CH340")
    self._claimed = True
    self._ctrl_out(_REQ_SERIAL_INIT, 0, 0)
    self._set_baud(self._baud)
    # Modem lines: DTR|RTS asserted (common CH340 init).
    self._ctrl_out(_REQ_MODEM_CTRL, 0x009F, 0x0000)

  def close(self) -> None:
    """Release interface and close the USB device."""
    lib = _LIB
    if lib is None:
      return
    if self._handle and self._claimed:
      try:
        self._ctrl_out(_REQ_MODEM_CTRL, 0x0000, 0x0000)
      except Exception as modem_error:
        print(f"ch340: modem clear: {modem_error}")
      lib.libusb_release_interface(self._handle, 0)
      self._claimed = False
    if self._handle:
      lib.libusb_close(self._handle)
      self._handle = c_void_p()
    if self._ctx:
      lib.libusb_exit(self._ctx)
      self._ctx = c_void_p()

  def write(self, data: bytes) -> None:
    """Write bytes to CH340 bulk OUT."""
    if not data:
      return
    lib = _libusb()
    buf = (c_ubyte * len(data)).from_buffer_copy(data)
    transferred = c_int(0)
    rc = lib.libusb_bulk_transfer(
      self._handle, _EP_OUT, buf, len(data), byref(transferred), self._timeout_ms,
    )
    if rc != 0 and transferred.value == 0:
      raise RuntimeError(f"CH340 bulk OUT failed rc={rc}")

  def read(self, max_len: int = 256) -> bytes:
    """Read up to ``max_len`` bytes from bulk IN (empty on timeout)."""
    lib = _libusb()
    buf = (c_ubyte * max_len)()
    transferred = c_int(0)
    rc = lib.libusb_bulk_transfer(
      self._handle, _EP_IN, buf, max_len, byref(transferred), self._timeout_ms,
    )
    if rc == -7:
      return b""
    if rc != 0 and transferred.value == 0:
      return b""
    return bytes(buf[: transferred.value])

  def _ctrl_out(self, request: int, value: int, index: int) -> None:
    lib = _libusb()
    rc = lib.libusb_control_transfer(
      self._handle,
      _REQ_VENDOR_WRITE,
      request & 0xFF,
      value & 0xFFFF,
      index & 0xFFFF,
      POINTER(c_ubyte)(),
      0,
      self._timeout_ms,
    )
    if rc < 0:
      raise RuntimeError(f"CH340 ctrl-out req=0x{request:02x} rc={rc}")

  def _set_baud(self, baud: int) -> None:
    """Program baud using the Linux ch341 divisor formula."""
    rate = max(50, int(baud))
    factor = _BAUDBASE // rate
    divisor = 3
    while factor > 0xFFF0 and divisor > 0:
      factor >>= 3
      divisor -= 1
    factor = 0x10000 - factor
    a = (factor & 0xFF00) | divisor
    b = factor & 0xFF
    self._ctrl_out(_REQ_WRITE_REG, 0x1312, a)
    self._ctrl_out(_REQ_WRITE_REG, 0x0F2C, b)


def _self_check() -> None:
  """ponytail: opens device if present; skips when unplugged."""
  port = Ch340UsbSerial(115200)
  try:
    port.open()
  except RuntimeError as exc:
    if "not found" in str(exc):
      print("ch340_usb_serial: skip (device absent)")
      return
    raise
  try:
    time.sleep(0.05)
    raw = port.read(64)
    print(f"ch340_usb_serial: open ok, rx={raw!r}")
  finally:
    port.close()


if __name__ == "__main__":
  _self_check()
