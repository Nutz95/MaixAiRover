"""Abstract I2C bus port used by the Hiwonder motor driver."""

from abc import ABC, abstractmethod
from typing import List


class I2cBus(ABC):
  """Hardware-agnostic I2C master operations."""

  @abstractmethod
  def scan(self) -> List[int]:
    """Return addresses that ACK on the bus."""

  @abstractmethod
  def write_bytes(self, address: int, register: int, data: bytes) -> None:
    """Write a register followed by a data payload."""

  @abstractmethod
  def read_bytes(self, address: int, register: int, length: int) -> bytes:
    """Write a register address then read ``length`` bytes."""
