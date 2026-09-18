"""Unit tests for MecanumMixer."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.drive_command import DriveCommand
from lib.mecanum_mixer import MecanumMixer


def test_idle_command_yields_zero_wheels():
  mixer = MecanumMixer(max_setpoint=50)
  speeds = mixer.mix(DriveCommand())
  assert speeds.front_left == 0
  assert speeds.front_right == 0
  assert speeds.rear_left == 0
  assert speeds.rear_right == 0


def test_forward_sets_same_sign_on_left_and_right_after_invert():
  mixer = MecanumMixer(max_setpoint=50)
  # Xbox forward is negative left_y after mapping convention (C++ negates again).
  speeds = mixer.mix(DriveCommand(axis_forward=-32767, max_speed=255))
  assert speeds.front_left > 0
  assert speeds.front_right > 0
  assert speeds.rear_left > 0
  assert speeds.rear_right > 0


def test_spin_left_opposes_left_and_right():
  mixer = MecanumMixer(max_setpoint=50)
  speeds = mixer.mix(DriveCommand(axis_spin=-32767, max_speed=255))
  assert speeds.front_left < 0
  assert speeds.rear_left < 0
  assert speeds.front_right > 0
  assert speeds.rear_right > 0


def test_max_speed_scales_magnitude():
  mixer = MecanumMixer(max_setpoint=50)
  full = mixer.mix(DriveCommand(axis_forward=-32767, max_speed=255))
  half = mixer.mix(DriveCommand(axis_forward=-32767, max_speed=128))
  assert abs(full.front_left) > abs(half.front_left)
