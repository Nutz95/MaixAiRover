"""Parsed ESP telemetry snapshot (binary TELEM response)."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from lib.esp_binary_protocol import (
  FLAG_IMU,
  FLAG_INA,
  FLAG_MAG,
  TELEM_SIZE,
  TELEM_STRUCT,
)


@dataclass(frozen=True)
class TelemSnapshot:
  """Fixed-layout telemetry from ESP ``RSP_TELEM``."""

  enc_fl: int
  enc_fr: int
  enc_rl: int
  enc_rr: int
  bus_mv: int
  current_ma: int
  ax: int
  ay: int
  az: int
  gx: int
  gy: int
  gz: int
  mx: int
  my: int
  mz: int
  temp_centi_c: int
  flags: int

  @classmethod
  def from_payload(cls, payload: bytes) -> "TelemSnapshot":
    """Decode a 42-byte little-endian telemetry payload."""
    if len(payload) < TELEM_SIZE:
      raise ValueError(f"telem payload short: {len(payload)}")
    values = struct.unpack_from(TELEM_STRUCT, payload, 0)
    return cls(
      enc_fl=values[0],
      enc_fr=values[1],
      enc_rl=values[2],
      enc_rr=values[3],
      bus_mv=values[4],
      current_ma=values[5],
      ax=values[6],
      ay=values[7],
      az=values[8],
      gx=values[9],
      gy=values[10],
      gz=values[11],
      mx=values[12],
      my=values[13],
      mz=values[14],
      temp_centi_c=values[15],
      flags=values[16],
    )

  @property
  def has_ina(self) -> bool:
    """True when INA219 fields are valid."""
    return (self.flags & FLAG_INA) != 0

  @property
  def has_imu(self) -> bool:
    """True when IMU fields are valid."""
    return (self.flags & FLAG_IMU) != 0

  @property
  def has_mag(self) -> bool:
    """True when magnetometer fields are valid."""
    return (self.flags & FLAG_MAG) != 0

  @property
  def temp_c(self) -> float:
    """IMU temperature in °C (0.0 if unavailable)."""
    return self.temp_centi_c / 100.0 if self.has_imu else 0.0
