"""Host checks for HUD instrument helpers (no MaixPy)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.hud_instruments import (
  LIPO_EMPTY_MV,
  LIPO_FULL_MV,
  battery_pct,
  cardinal_fr,
  heading_deg,
  pitch_roll_deg,
)
from lib.telem_snapshot import TelemSnapshot


def test_cardinals_and_battery() -> None:
  assert cardinal_fr(0) == "N"
  assert cardinal_fr(180) == "S"
  assert cardinal_fr(270) == "O"
  assert battery_pct(LIPO_EMPTY_MV) == 0
  assert battery_pct(LIPO_FULL_MV) == 100
  assert battery_pct(12240) == 83


def test_heading_and_attitude() -> None:
  assert heading_deg(0, 100) is not None
  flat = pitch_roll_deg(0, 0, 1000)
  assert flat is not None
  assert abs(flat.pitch_deg) < 1.0 and abs(flat.roll_deg) < 1.0


def test_from_telem_mag_only() -> None:
  from lib.hud_instruments import from_telem

  snap = TelemSnapshot(
    enc_fl=0, enc_fr=0, enc_rl=0, enc_rr=0,
    bus_mv=12240, current_ma=100,
    ax=0, ay=0, az=0, gx=0, gy=0, gz=0,
    mx=100, my=0, mz=0, temp_centi_c=0,
    flags=0x06,  # mag|ina
  )
  inst = from_telem(snap)
  assert inst.cardinal == "N"
  assert inst.battery_pct == 83
  assert inst.pitch_deg is None


def main() -> None:
  test_cardinals_and_battery()
  test_heading_and_attitude()
  test_from_telem_mag_only()
  print("hud_instruments: ok")


if __name__ == "__main__":
  main()
