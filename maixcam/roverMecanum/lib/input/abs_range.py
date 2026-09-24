"""Typed ABS axis range (min/max/flat) without tuple DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbsRange:
  """Kernel or fallback absolute-axis range metadata."""

  minimum: int
  maximum: int
  flat: int
