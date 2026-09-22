"""Wire config into a ready MotionController stack."""

from lib.dual_board_drive_port import DualBoardDrivePort
from lib.encoder_odometry import EncoderOdometry
from lib.esp_pair_drive_board import EspPairDriveBoard
from lib.hiwonder_motor_driver import HiwonderMotorDriver
from lib.i2c_bus_factory import I2cBusFactory
from lib.i2c_config import I2cConfig
from lib.mecanum_mixer import MecanumMixer
from lib.motion_controller import MotionController
from lib.motor_config import MotorConfig
from lib.null_rear_drive_board import NullRearDriveBoard
from lib.rover_motion_client import RoverMotionClient
from lib.stub_i2c_bus import StubI2cBus


class MotionStackFactory:
  """Build the motion client (ESP dual-board or legacy stub) from config."""

  def create(self, config: dict) -> RoverMotionClient:
    """Legacy stub/I2C path (host tests). Prefer ``create_esp`` on device."""
    i2c_cfg = I2cConfig.from_mapping(config.get("i2c", {}))
    motor_cfg = MotorConfig.from_mapping(config.get("motors", {}))
    bus = I2cBusFactory().create(i2c_cfg)
    driver = HiwonderMotorDriver(bus, i2c_cfg.address, motor_cfg)
    client = self._wrap(driver, motor_cfg, is_stub=isinstance(bus, StubI2cBus))
    print(
      f"i2c mode={i2c_cfg.mode} effective="
      f"{'stub' if isinstance(bus, StubI2cBus) else i2c_cfg.mode}"
    )
    return client

  def create_esp(
    self,
    config: dict,
    set_front_drive,
    set_rear_drive=None,
  ) -> RoverMotionClient:
    """Mecanum mix on Maix → front ESP pump + optional rear pump."""
    motor_cfg = MotorConfig.from_mapping(config.get("motors", {}))
    front = EspPairDriveBoard(set_front_drive, max_setpoint=motor_cfg.max_setpoint)
    if set_rear_drive is not None:
      rear = EspPairDriveBoard(set_rear_drive, max_setpoint=motor_cfg.max_setpoint)
      rear_label = "ESP rear (UART pump)"
    else:
      rear = NullRearDriveBoard()
      rear_label = "rear stub"
    driver = DualBoardDrivePort(front, rear)
    client = self._wrap(driver, motor_cfg, is_stub=False)
    print(f"drive: mecanum → ESP front (UART pump) + {rear_label}")
    return client

  def _wrap(self, driver, motor_cfg: MotorConfig, *, is_stub: bool) -> RoverMotionClient:
    mixer = MecanumMixer(max_setpoint=motor_cfg.max_setpoint)
    odometry = EncoderOdometry(motor_cfg)
    motion = MotionController(driver, mixer, odometry, motor_cfg)
    client = RoverMotionClient(motion, is_stub=is_stub)
    try:
      motion.initialize(settle_s=0.0)
    except Exception as exc:
      print(f"motion init: {exc}")
      client.note_i2c_error(str(exc))
    return client
