"""Typed I2C configuration loaded from config.json."""

from dataclasses import dataclass


@dataclass(frozen=True)
class I2cConfig:
  """I2C connection settings for stub or hardware mode."""

  mode: str = "stub"
  bus_id: int = 6
  address: int = 0x34
  scl_pin: str = "A1"
  scl_function: str = "I2C6_SCL"
  sda_pin: str = "A0"
  sda_function: str = "I2C6_SDA"

  @staticmethod
  def from_mapping(raw: dict) -> "I2cConfig":
    """Build an I2cConfig from a config.json ``i2c`` object."""
    if not isinstance(raw, dict):
      raw = {}
    mode = str(raw.get("mode", "stub")).strip().lower()
    if mode not in ("stub", "hardware"):
      mode = "stub"
    return I2cConfig(
      mode=mode,
      bus_id=int(raw.get("id", 6)),
      address=int(raw.get("addr", 0x34)),
      scl_pin=str(raw.get("scl", "A1")),
      scl_function=str(raw.get("scl_function", "I2C6_SCL")),
      sda_pin=str(raw.get("sda", "A0")),
      sda_function=str(raw.get("sda_function", "I2C6_SDA")),
    )
