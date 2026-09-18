"""Cumulative encoder pulse counts from the Hiwonder board."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EncoderCounts:
  """Little-endian int32 pulse totals for channels M1..M4."""

  m1: int = 0
  m2: int = 0
  m3: int = 0
  m4: int = 0
