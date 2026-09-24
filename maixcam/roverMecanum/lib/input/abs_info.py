"""Typed ABS axis sample from EVIOCGABS (value + range)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbsInfo:
  """Current ABS value plus range from the Linux input_absinfo struct."""

  value: int
  minimum: int
  maximum: int
  flat: int
