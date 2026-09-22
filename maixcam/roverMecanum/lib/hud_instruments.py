"""Derive HUD values from ESP telemetry (heading, battery %, pitch/roll)."""

from __future__ import annotations

import math
from dataclasses import dataclass

# 3S LiPo pack on Waveshare 12 V rail.
LIPO_EMPTY_MV = 10500
LIPO_FULL_MV = 12600  # 3 × 4.2 V

_CARDINALS_FR = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


@dataclass(frozen=True)
class HudInstruments:
  """Values ready for HUD drawing (None = sensor missing this frame)."""

  heading_deg: float | None
  cardinal: str | None
  pitch_deg: float | None
  roll_deg: float | None
  battery_pct: int | None
  bus_mv: int | None


def heading_deg(mx: int, my: int) -> float | None:
  """Compass heading in degrees [0, 360) from mag X/Y, or None if too weak."""
  if mx == 0 and my == 0:
    return None
  deg = math.degrees(math.atan2(float(my), float(mx)))
  if deg < 0.0:
    deg += 360.0
  return deg


def cardinal_fr(deg: float) -> str:
  """Map degrees to French 8-wind cardinal (N/NE/E/SE/S/SO/O/NO)."""
  idx = int((deg + 22.5) // 45.0) % 8
  return _CARDINALS_FR[idx]


def battery_pct(bus_mv: int, empty_mv: int = LIPO_EMPTY_MV, full_mv: int = LIPO_FULL_MV) -> int:
  """Linear SoC percent for a 3S LiPo (clamped 0..100)."""
  span = max(1, full_mv - empty_mv)
  return max(0, min(100, int(round((bus_mv - empty_mv) * 100 / span))))


def pitch_roll_deg(ax: int, ay: int, az: int) -> tuple[float, float] | None:
  """Rough pitch/roll from accelerometer (degrees). None if vector ~0."""
  fx, fy, fz = float(ax), float(ay), float(az)
  norm = math.sqrt(fx * fx + fy * fy + fz * fz)
  if norm < 1.0:
    return None
  fx /= norm
  fy /= norm
  fz /= norm
  pitch = math.degrees(math.atan2(-fx, math.sqrt(fy * fy + fz * fz)))
  roll = math.degrees(math.atan2(fy, fz))
  return pitch, roll


def from_telem(telem) -> HudInstruments:
  """Build HUD instruments from a TelemSnapshot (or None)."""
  if telem is None:
    return HudInstruments(None, None, None, None, None, None)
  heading = None
  cardinal = None
  if telem.has_mag:
    heading = heading_deg(telem.mx, telem.my)
    if heading is not None:
      cardinal = cardinal_fr(heading)
  pitch = None
  roll = None
  if telem.has_imu:
    pr = pitch_roll_deg(telem.ax, telem.ay, telem.az)
    if pr is not None:
      pitch, roll = pr
  pct = None
  bus = None
  if telem.has_ina:
    bus = int(telem.bus_mv)
    pct = battery_pct(bus)
  return HudInstruments(heading, cardinal, pitch, roll, pct, bus)


def _self_check() -> None:
  assert cardinal_fr(0) == "N"
  assert cardinal_fr(45) == "NE"
  assert cardinal_fr(90) == "E"
  assert cardinal_fr(225) == "SO"
  assert cardinal_fr(315) == "NO"
  assert battery_pct(LIPO_EMPTY_MV) == 0
  assert battery_pct(LIPO_FULL_MV) == 100
  assert battery_pct(11550) == 50
  h = heading_deg(100, 0)
  assert h is not None and abs(h - 0.0) < 1e-6
  pr = pitch_roll_deg(0, 0, 1000)
  assert pr is not None and abs(pr[0]) < 1.0 and abs(pr[1]) < 1.0


_self_check()
