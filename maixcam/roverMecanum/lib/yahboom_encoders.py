"""Yahboom encoder tick totals M1..M4."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YahboomEncoders:
  """Raw encoder ticks from ``FUNC_REPORT_ENCODER``."""

  m1: int
  m2: int
  m3: int
  m4: int
