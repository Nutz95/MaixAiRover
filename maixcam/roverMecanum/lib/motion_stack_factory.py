"""Wire config into a ready MotionController stack."""

from lib.encoder_odometry import EncoderOdometry
from lib.hiwonder_motor_driver import HiwonderMotorDriver
from lib.i2c_bus_factory import I2cBusFactory
from lib.i2c_config import I2cConfig
from lib.mecanum_mixer import MecanumMixer
from lib.motion_controller import MotionController
from lib.motor_config import MotorConfig
from lib.rover_motion_client import RoverMotionClient
from lib.stub_i2c_bus import StubI2cBus


class MotionStackFactory:
  """Build the motion client (stub or hardware) from application config."""

  def create(self, config: dict) -> RoverMotionClient:
    """Create, initialize, and return a RoverMotionClient."""
    i2c_cfg = I2cConfig.from_mapping(config.get("i2c", {}))
    motor_cfg = MotorConfig.from_mapping(config.get("motors", {}))
    bus = I2cBusFactory().create(i2c_cfg)
    driver = HiwonderMotorDriver(bus, i2c_cfg.address, motor_cfg)
    mixer = MecanumMixer(max_setpoint=motor_cfg.max_setpoint)
    odometry = EncoderOdometry(motor_cfg)
    motion = MotionController(driver, mixer, odometry, motor_cfg)
    client = RoverMotionClient(motion)
    found = bus.scan()
    effective = "stub" if isinstance(bus, StubI2cBus) else i2c_cfg.mode
    print(
      f"i2c mode={i2c_cfg.mode} effective={effective} "
      f"addr=0x{i2c_cfg.address:02x} scan={[hex(a) for a in found]}"
    )
    try:
      reading = driver.read_battery()
      client.set_battery(reading)
      print(
        f"i2c ADC_BAT={reading.millivolts} mV ({reading.millivolts / 1000.0:.2f} V)"
      )
    except Exception as exc:
      print(f"i2c ADC_BAT failed: {exc}")
      client.note_i2c_error(str(exc))
      return client
    try:
      motion.initialize(settle_s=0.5 if effective == "hardware" else 0.0)
      encoders = driver.read_encoders()
      print(
        f"i2c encoders M1={encoders.m1} M2={encoders.m2} "
        f"M3={encoders.m3} M4={encoders.m4}"
      )
    except Exception as exc:
      print(f"i2c init failed: {exc}")
      client.note_i2c_error(str(exc))
    return client
