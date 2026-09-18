"""MaixCAM2 hardware I2C6 bus (Phase 1B)."""

import time
from typing import List

from maix import err, i2c, pinmap

from lib.hiwonder_registers import HiwonderRegisters
from lib.i2c_bus import I2cBus


class MaixI2cBus(I2cBus):
  """I2C master using MaixPy pinmap + peripheral I2C."""

  def __init__(
    self,
    bus_id: int = 6,
    scl_pin: str = "A1",
    scl_function: str = "I2C6_SCL",
    sda_pin: str = "A0",
    sda_function: str = "I2C6_SDA",
    freq: int = 100000,
  ) -> None:
    err.check_raise(pinmap.set_pin_function(scl_pin, scl_function), "SCL pinmap failed")
    err.check_raise(pinmap.set_pin_function(sda_pin, sda_function), "SDA pinmap failed")
    self._bus_id = bus_id
    self._freq = freq
    self._scl = f"{scl_pin}/{scl_function}"
    self._sda = f"{sda_pin}/{sda_function}"
    self._bus = i2c.I2C(bus_id, i2c.Mode.MASTER, freq)
    self._next_try_s = 0.0
    self._last_error = ""
    found = self.scan()
    print(
      f"i2c{bus_id} {self._sda} {self._scl} {freq}Hz scan="
      f"{[hex(a) for a in found]}"
    )
    if HiwonderRegisters.DEFAULT_ADDRESS not in found:
      self._last_error = (
        f"I2C{bus_id} scan empty, 0x34 missing — "
        "12V on driver + GND common + A0=SDA A1=SCL"
      )
      print(f"i2c: {self._last_error}")

  def scan(self) -> List[int]:
    """Scan the physical I2C bus for ACK addresses."""
    try:
      return list(self._bus.scan())
    except Exception as exc:
      print(f"i2c: scan failed: {exc}")
      return []

  def write_bytes(self, address: int, register: int, data: bytes) -> None:
    """Write a register via SMBus-style ``writeto_mem`` (Hiwonder protocol)."""
    now = time.monotonic()
    if now < self._next_try_s:
      raise OSError(self._last_error or "i2c cooldown")
    payload = bytes(data)
    ret = -1
    for attempt in range(3):
      try:
        ret = int(self._bus.writeto_mem(address, register, payload))
      except Exception as exc:
        self._last_error = f"I2C{self._bus_id} write exception: {exc}"
        ret = -1
      if ret >= 0:
        self._last_error = ""
        return
      time.sleep(0.01)
    self._next_try_s = now + 1.0
    found = self.scan()
    self._last_error = (
      f"I2C{self._bus_id} NACK {hex(address)} reg={hex(register)}"
      f" data={payload.hex()} ret={ret} scan={[hex(a) for a in found]}"
      f" — 12V+GND+{self._sda}+{self._scl}"
    )
    raise OSError(self._last_error)

  def read_bytes(self, address: int, register: int, length: int) -> bytes:
    """Read ``length`` bytes from a register via ``readfrom_mem``."""
    now = time.monotonic()
    if now < self._next_try_s:
      raise OSError(self._last_error or "i2c cooldown")
    raw = None
    for _attempt in range(3):
      try:
        raw = self._bus.readfrom_mem(address, register, length)
      except Exception as exc:
        self._last_error = f"I2C{self._bus_id} read exception: {exc}"
        raw = None
      if raw is not None:
        self._last_error = ""
        return bytes(raw)
      time.sleep(0.01)
    self._next_try_s = now + 1.0
    found = self.scan()
    self._last_error = (
      f"I2C{self._bus_id} read fail {hex(address)} reg={hex(register)}"
      f" scan={[hex(a) for a in found]} — 12V+GND+{self._sda}+{self._scl}"
    )
    raise OSError(self._last_error)
