"""Reply from a blocking ESP binary exchange."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EspExchangeResult:
  """Command type and payload returned by ``_exchange``."""

  cmd: int
  payload: bytes
