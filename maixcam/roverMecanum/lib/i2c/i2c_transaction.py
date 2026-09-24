"""Logged I2C register transaction for stub/debug."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class I2cTransaction:
  """One write or read against a register on the motor driver."""

  address: int
  register: int
  is_write: bool
  data: bytes
  note: Optional[str] = None
