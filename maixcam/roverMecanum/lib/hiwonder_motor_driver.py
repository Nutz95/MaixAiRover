"""Hiwonder 4-channel encoder motor driver over an injected I2cBus."""

import struct
import time
from typing import List

from lib.battery_reading import BatteryReading
from lib.encoder_counts import EncoderCounts
from lib.hiwonder_registers import HiwonderRegisters
from lib.i2c_bus import I2cBus
from lib.motor_config import MotorConfig
from lib.wheel_speeds import WheelSpeeds


class HiwonderMotorDriver:
  """Register-level control of the Hiwonder encoder motor board."""

  def __init__(self, bus: I2cBus, address: int, motor_config: MotorConfig) -> None:
    self._bus = bus
    self._address = address
    self._config = motor_config
    self._initialized = False
    self._last_speed_payload = None

  def initialize(self, settle_s: float = 0.0) -> None:
    """Program motor type and encoder polarity (required once after power-up)."""
    self._bus.write_bytes(
      self._address,
      HiwonderRegisters.MOTOR_TYPE,
      bytes([self._config.motor_type & 0xFF]),
    )
    # ponytail: Hiwonder MCU needs ~500ms after MOTOR_TYPE (official TankDemo).
    if settle_s > 0:
      time.sleep(settle_s)
    self._bus.write_bytes(
      self._address,
      HiwonderRegisters.ENCODER_POLARITY,
      bytes([self._config.encoder_polarity & 0xFF]),
    )
    self._initialized = True
    self._last_speed_payload = None

  def set_wheel_speeds(self, speeds: WheelSpeeds) -> None:
    """Write closed-loop or open-loop setpoints for all four channels."""
    channels = self._map_to_channels(speeds)
    payload = self._pack_int8(channels)
    if payload == self._last_speed_payload:
      return
    register = (
      HiwonderRegisters.FIXED_SPEED
      if self._config.control_mode == "speed"
      else HiwonderRegisters.FIXED_PWM
    )
    self._bus.write_bytes(self._address, register, payload)
    self._last_speed_payload = payload

  def stop(self) -> None:
    """Command all motors to zero setpoint."""
    self.set_wheel_speeds(WheelSpeeds())

  def read_encoders(self) -> EncoderCounts:
    """Read cumulative encoder pulse totals for M1..M4."""
    raw = self._bus.read_bytes(self._address, HiwonderRegisters.ENCODER_TOTAL, 16)
    values = struct.unpack("<iiii", raw)
    return EncoderCounts(m1=values[0], m2=values[1], m3=values[2], m4=values[3])

  def clear_encoders(self) -> None:
    """Reset cumulative encoder counters to zero."""
    self._bus.write_bytes(self._address, HiwonderRegisters.ENCODER_TOTAL, bytes(16))

  def read_battery(self) -> BatteryReading:
    """Read the motor-supply ADC value in millivolts."""
    raw = self._bus.read_bytes(self._address, HiwonderRegisters.ADC_BAT, 2)
    millivolts = raw[0] + (raw[1] << 8)
    return BatteryReading(millivolts=millivolts)

  def _map_to_channels(self, speeds: WheelSpeeds) -> List[int]:
    named = {
      "FL": speeds.front_left,
      "FR": speeds.front_right,
      "RL": speeds.rear_left,
      "RR": speeds.rear_right,
    }
    ordered: List[int] = []
    invert = self._config.invert
    for index, label in enumerate(self._config.channel_order):
      value = int(named.get(label.upper(), 0))
      if index < len(invert) and invert[index]:
        value = -value
      ordered.append(value)
    while len(ordered) < 4:
      ordered.append(0)
    return ordered[:4]

  def _pack_int8(self, values: List[int]) -> bytes:
    limit = 100 if self._config.control_mode == "pwm" else self._config.max_setpoint
    out = bytearray(4)
    for index in range(4):
      clamped = max(-limit, min(limit, int(values[index])))
      out[index] = clamped & 0xFF
    return bytes(out)
