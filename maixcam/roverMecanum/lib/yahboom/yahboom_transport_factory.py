"""Factory for Yahboom byte transport (CH340 libusb or pyserial path)."""

from __future__ import annotations

from lib.motion.byte_transport import ByteTransport
from lib.yahboom.ch340_usb_serial import Ch340UsbSerial
from lib.yahboom.yahboom_serial_transport import YahboomSerialTransport


class YahboomTransportFactory:
  """Pick CH340 libusb on Maix (no ttyUSB) or an explicit serial device path."""

  AUTO_NAMES = ("", "auto", "usb", "ch340")

  def create(self, port: str, baud: int = 115200) -> ByteTransport:
    """Build a transport for ``yahboom.port`` config."""
    name = (port or "").strip()
    if name.lower() in self.AUTO_NAMES:
      return Ch340UsbSerial(baud=baud)
    return YahboomSerialTransport(name, baud=baud)
