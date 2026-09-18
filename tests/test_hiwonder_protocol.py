"""Unit tests for Hiwonder protocol over StubI2cBus."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.hiwonder_motor_driver import HiwonderMotorDriver
from lib.hiwonder_registers import HiwonderRegisters
from lib.motion_stack_factory import MotionStackFactory
from lib.motor_config import MotorConfig
from lib.stub_i2c_bus import StubI2cBus
from lib.wheel_speeds import WheelSpeeds


def test_stub_scan_finds_default_address():
  bus = StubI2cBus()
  assert HiwonderRegisters.DEFAULT_ADDRESS in bus.scan()


def test_initialize_writes_type_and_polarity():
  bus = StubI2cBus()
  cfg = MotorConfig(motor_type=3, encoder_polarity=0)
  driver = HiwonderMotorDriver(bus, 0x34, cfg)
  driver.initialize()
  regs = [t.register for t in bus.transactions() if t.is_write]
  assert HiwonderRegisters.MOTOR_TYPE in regs
  assert HiwonderRegisters.ENCODER_POLARITY in regs


def test_set_speeds_writes_fixed_speed_register():
  bus = StubI2cBus()
  driver = HiwonderMotorDriver(bus, 0x34, MotorConfig())
  driver.initialize()
  bus.clear_transactions()
  driver.set_wheel_speeds(WheelSpeeds(front_left=20, front_right=-20, rear_left=10, rear_right=-10))
  writes = [t for t in bus.transactions() if t.is_write and t.register == HiwonderRegisters.FIXED_SPEED]
  assert len(writes) == 1
  assert writes[0].data[0] == 20
  assert writes[0].data[1] == (-20) & 0xFF


def test_duplicate_speed_write_skipped():
  bus = StubI2cBus()
  driver = HiwonderMotorDriver(bus, 0x34, MotorConfig())
  driver.initialize()
  bus.clear_transactions()
  speeds = WheelSpeeds(front_left=20, front_right=-20, rear_left=10, rear_right=-10)
  driver.set_wheel_speeds(speeds)
  driver.set_wheel_speeds(speeds)
  writes = [t for t in bus.transactions() if t.is_write and t.register == HiwonderRegisters.FIXED_SPEED]
  assert len(writes) == 1


def test_register_name():
  assert HiwonderRegisters.FIXED_SPEED == 0x33
  assert HiwonderRegisters.FIXED_SPEED.name == "FIXED_SPEED"


def test_factory_reads_battery_at_create():
  client = MotionStackFactory().create(
    {"i2c": {"mode": "stub", "addr": 52}, "motors": {}}
  )
  reading = client.last_battery()
  assert reading is not None
  assert reading.millivolts == 12000
  assert client.last_i2c_error() == ""


def test_battery_and_encoders_roundtrip():
  bus = StubI2cBus()
  driver = HiwonderMotorDriver(bus, 0x34, MotorConfig())
  driver.initialize()
  assert driver.read_battery().millivolts == 12000
  driver.set_wheel_speeds(WheelSpeeds(front_left=5, front_right=5, rear_left=5, rear_right=5))
  counts = driver.read_encoders()
  assert counts.m1 != 0
  driver.clear_encoders()
  cleared = driver.read_encoders()
  assert cleared.m1 == 0
