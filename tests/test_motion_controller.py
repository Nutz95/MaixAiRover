"""Unit tests for MotionController turn_degrees on stub bus."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.motion.drive_command import DriveCommand
from lib.motion.encoder_odometry import EncoderOdometry
from lib.motion.hiwonder_motor_driver import HiwonderMotorDriver
from lib.motion.mecanum_mixer import MecanumMixer
from lib.motion.motion_controller import MotionController
from lib.config.motor_config import MotorConfig
from lib.i2c.stub_i2c_bus import StubI2cBus


def _controller() -> MotionController:
  cfg = MotorConfig(max_setpoint=50, track_width_mm=200.0, wheel_diameter_mm=96.0, gear_ratio=56.0)
  bus = StubI2cBus()
  driver = HiwonderMotorDriver(bus, 0x34, cfg)
  mixer = MecanumMixer(max_setpoint=50)
  odo = EncoderOdometry(cfg)
  motion = MotionController(mixer, odo, cfg, wheel_driver=driver)
  motion.initialize()
  return motion


def test_turn_degrees_completes_on_stub():
  motion = _controller()
  ok = motion.turn_degrees(20.0, setpoint=20, timeout_s=2.0, poll_s=0.0)
  assert ok is True
  assert motion.last_wheel_speeds().front_left == 0


def test_jog_wheel_drives_only_named_channel():
  motion = _controller()
  speeds = motion.jog_wheel("FR", 1)
  assert speeds.front_right == 50
  assert speeds.front_left == 0
  assert speeds.rear_left == 0
  assert speeds.rear_right == 0
  reverse = motion.jog_wheel("RL", -1)
  assert reverse.rear_left == -50
  assert reverse.front_right == 0
  motion.stop()
  assert motion.last_wheel_speeds().rear_left == 0


def test_drive_updates_last_wheel_speeds():
  motion = _controller()
  speeds = motion.drive(DriveCommand(axis_forward=-32767, max_speed=255))
  assert speeds.front_left != 0
  assert motion.last_wheel_speeds().front_left == speeds.front_left
  motion.stop()
