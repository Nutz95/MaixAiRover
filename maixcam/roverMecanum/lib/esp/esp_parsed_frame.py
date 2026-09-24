"""Result of parsing one ESP binary RX frame."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EspParsedFrame:
  """One decoded frame: command type, payload, and leftover buffer bytes."""

  cmd: int
  payload: bytes
  rest: bytes
