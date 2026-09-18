"""In-memory I2C bus stub for Phase 1A (no motor board wired)."""

from typing import Dict, List

from lib.hiwonder_registers import HiwonderRegisters
from lib.i2c_bus import I2cBus
from lib.i2c_transaction import I2cTransaction


class StubI2cBus(I2cBus):
  """Simulates the Hiwonder slave at 0x34 including encoder integration."""

  def __init__(self, slave_address: int = HiwonderRegisters.DEFAULT_ADDRESS) -> None:
    self._slave_address = slave_address
    self._memory: Dict[int, bytearray] = {}
    self._transactions: List[I2cTransaction] = []
    self._last_speeds = [0, 0, 0, 0]
    self._encoders = [0, 0, 0, 0]
    self._battery_mv = 12000
    self._record_enabled = True

  def enable_recording(self, enabled: bool) -> None:
    """Enable or disable transaction logging."""
    self._record_enabled = enabled

  def transactions(self) -> List[I2cTransaction]:
    """Return a copy of recorded transactions."""
    return list(self._transactions)

  def clear_transactions(self) -> None:
    """Drop the transaction log."""
    self._transactions.clear()

  def scan(self) -> List[int]:
    """Always report the configured Hiwonder address as present."""
    return [self._slave_address]

  def write_bytes(self, address: int, register: int, data: bytes) -> None:
    """Store register payload and update simulated motor/encoder state."""
    if address != self._slave_address:
      return
    payload = bytes(data)
    self._memory[register] = bytearray(payload)
    if self._record_enabled:
      self._transactions.append(
        I2cTransaction(address=address, register=register, is_write=True, data=payload)
      )
    if register == HiwonderRegisters.FIXED_SPEED or register == HiwonderRegisters.FIXED_PWM:
      self._apply_setpoints(payload)
    elif register == HiwonderRegisters.ENCODER_TOTAL and payload == bytes(16):
      self._encoders = [0, 0, 0, 0]
      self._last_speeds = [0, 0, 0, 0]

  def read_bytes(self, address: int, register: int, length: int) -> bytes:
    """Serve battery, encoders, or last written register contents."""
    if address != self._slave_address:
      return bytes(length)
    if register == HiwonderRegisters.ADC_BAT:
      value = self._battery_mv & 0xFFFF
      result = bytes([value & 0xFF, (value >> 8) & 0xFF])[:length]
    elif register == HiwonderRegisters.ENCODER_TOTAL:
      self._integrate_encoders()
      result = b"".join(int(v).to_bytes(4, "little", signed=True) for v in self._encoders)
      result = result[:length]
    else:
      stored = self._memory.get(register, bytearray())
      result = bytes(stored[:length])
      if len(result) < length:
        result = result + bytes(length - len(result))
    if self._record_enabled:
      self._transactions.append(
        I2cTransaction(address=address, register=register, is_write=False, data=result)
      )
    return result

  def _apply_setpoints(self, payload: bytes) -> None:
    speeds = [0, 0, 0, 0]
    for index in range(min(4, len(payload))):
      raw = payload[index]
      if raw > 127:
        speeds[index] = raw - 256
      else:
        speeds[index] = raw
    self._last_speeds = speeds
    self._integrate_encoders()

  def _integrate_encoders(self) -> None:
    for index in range(4):
      self._encoders[index] += int(self._last_speeds[index]) * 8
