"""Right-stick ABS_Z/ABS_RZ must use stick range, not trigger defaults."""

from lib.input.abs_range import AbsRange
from lib.input.evdev_axis_mapper import EvdevAxisMapper
from lib.input.evdev_constants import ABS_RZ, ABS_Z, ABS_GAS, AXIS_MAX, default_abs_range


def test_z_rz_default_to_stick_range():
  assert default_abs_range(ABS_Z) == AbsRange(0, 65535, 4096)
  assert default_abs_range(ABS_RZ) == AbsRange(0, 65535, 4096)
  assert default_abs_range(ABS_GAS) == AbsRange(0, 1023, 64)
  assert default_abs_range(ABS_Z, prefer_trigger=True) == AbsRange(0, 1023, 64)


def test_right_stick_rest_centers_with_stick_range():
  # Xbox BLE rest ~ mid of 0..65535; wrong 0..1023 range saturates +AXIS_MAX.
  mapper = EvdevAxisMapper(0, 65535, 4096)
  mapper.set_raw(32768)
  assert mapper.to_axis() == 0


def test_wrong_trigger_range_saturates_at_rest():
  mapper = EvdevAxisMapper(0, 1023, 64)
  mapper.set_raw(32768)
  assert mapper.to_axis() == AXIS_MAX
