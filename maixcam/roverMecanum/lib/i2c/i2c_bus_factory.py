"""Factory that builds stub or hardware I2C buses from config."""

from lib.i2c.i2c_bus import I2cBus
from lib.i2c.i2c_config import I2cConfig
from lib.i2c.stub_i2c_bus import StubI2cBus


class I2cBusFactory:
  """Create the I2C bus implementation selected by configuration."""

  def create(self, config: I2cConfig) -> I2cBus:
    """Return a stub bus or a MaixCAM hardware bus.

    Hardware mode falls back to stub when the motor board is missing so the
    Xbox HUD app can still start without a wired driver.
    """
    if config.mode != "hardware":
      return StubI2cBus(slave_address=config.address)

    from lib.i2c.maix_i2c_bus import MaixI2cBus

    try:
      bus = MaixI2cBus(
        bus_id=config.bus_id,
        scl_pin=config.scl_pin,
        scl_function=config.scl_function,
        sda_pin=config.sda_pin,
        sda_function=config.sda_function,
      )
    except Exception as exc:
      print(f"i2c: hardware open failed ({exc}); using stub")
      return StubI2cBus(slave_address=config.address)

    found = bus.scan()
    if config.address not in found:
      print(
        f"i2c: 0x{config.address:02x} missing on bus "
        f"(scan={[hex(a) for a in found]}); using stub"
      )
      return StubI2cBus(slave_address=config.address)
    return bus
