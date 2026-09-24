"""Unit tests for controller mapping revision 4."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.input.controller_button import ControllerButton
from lib.input.controller_mapping_engine import ControllerMappingEngine
from lib.input.controller_state import ControllerState
from lib.input.drive_action import DriveAction


def _config():
  return {
    "rover": {
      "deadzone_percent": 5,
      "axis_sensitivity_percent": 100,
      "axis_expo": 1.0,
      "axis_curve": "linear",
    },
    "mapping": {
      "axes": {
        "drive_forward": "left_y",
        "drive_strafe": "trigger_diff",
        "drive_spin": "right_x",
        "drive_pivot": "left_x",
      },
      "invert": {},
      "dpad": {
        "up": "forward",
        "down": "backward",
        "left": "strafe_left",
        "right": "strafe_right",
      },
      "buttons": {"btn_a": "stop"},
    },
  }


def test_left_y_maps_to_forward_axis():
  engine = ControllerMappingEngine(_config())
  state = ControllerState()
  state.left_y = -20000
  out = engine.compute(state)
  assert out.axis_forward < 0
  assert out.axis_strafe == 0


def test_trigger_diff_maps_to_strafe():
  engine = ControllerMappingEngine(_config())
  state = ControllerState()
  state.rt = 20000
  state.lt = 0
  out = engine.compute(state)
  assert out.axis_strafe > 0


def test_dpad_up_overrides_sticks():
  engine = ControllerMappingEngine(_config())
  state = ControllerState()
  state.left_y = 10000
  state.dpad_y = -1
  out = engine.compute(state)
  assert out.axis_forward < 0
  assert out.axis_spin == 0


def test_button_a_sets_stop_preset_action():
  engine = ControllerMappingEngine(_config())
  state = ControllerState()
  state.pressed_edge[ControllerButton.A] = True
  out = engine.compute(state)
  assert out.preset_action is DriveAction.STOP
