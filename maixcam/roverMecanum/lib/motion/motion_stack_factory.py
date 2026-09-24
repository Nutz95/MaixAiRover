"""Wire config into a ready MotionController stack."""

from lib.motion.drive_backend_config import DriveBackendConfig
from lib.motion.drive_backend_kind import DriveBackendKind
from lib.motion.drive_command_chassis_mapper import DriveCommandChassisMapper
from lib.motion.dual_board_drive_port import DualBoardDrivePort
from lib.motion.encoder_odometry import EncoderOdometry
from lib.esp.esp_pair_drive_board import EspPairDriveBoard
from lib.motion.hiwonder_motor_driver import HiwonderMotorDriver
from lib.i2c.i2c_bus_factory import I2cBusFactory
from lib.i2c.i2c_config import I2cConfig
from lib.motion.mecanum_mixer import MecanumMixer
from lib.motion.motion_controller import MotionController
from lib.motion.motion_stack_bundle import MotionStackBundle
from lib.config.motor_config import MotorConfig
from lib.motion.null_rear_drive_board import NullRearDriveBoard
from lib.motion.rover_motion_client import RoverMotionClient
from lib.i2c.stub_i2c_bus import StubI2cBus
from lib.yahboom.yahboom_drive_board import YahboomDriveBoard
from lib.yahboom.yahboom_transport_factory import YahboomTransportFactory


class MotionStackFactory:
  """Build the motion client (ESP dual-board, Yahboom, or legacy stub)."""

  def create(self, config: dict) -> RoverMotionClient:
    """Legacy stub/I2C path (host tests). Prefer ``create_esp`` on device."""
    i2c_cfg = I2cConfig.from_mapping(config.get("i2c", {}))
    motor_cfg = MotorConfig.from_mapping(config.get("motors", {}))
    bus = I2cBusFactory().create(i2c_cfg)
    driver = HiwonderMotorDriver(bus, i2c_cfg.address, motor_cfg)
    client = self._wrap_wheels(driver, motor_cfg, is_stub=isinstance(bus, StubI2cBus))
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
  ) -> MotionStackBundle:
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
    client = self._wrap_wheels(driver, motor_cfg, is_stub=False)
    print(f"drive: mecanum → ESP front (UART pump) + {rear_label}")
    return MotionStackBundle(client=client, yahboom_board=None)

  def create_yahboom(self, config: dict) -> MotionStackBundle:
    """Closed-loop chassis on Yahboom (STM32 PID + encoders via set_car_motion)."""
    motor_cfg = MotorConfig.from_mapping(config.get("motors", {}))
    backend = DriveBackendConfig.from_root(config)
    if backend.kind != DriveBackendKind.YAHBOOM:
      raise ValueError("create_yahboom requires drive_backend=yahboom")
    yahboom_cfg = backend.yahboom
    transport = YahboomTransportFactory().create(yahboom_cfg.port, baud=yahboom_cfg.baud)
    board = YahboomDriveBoard(transport, yahboom_cfg)
    mapper = DriveCommandChassisMapper(yahboom_cfg)
    client = self._wrap_chassis(board, mapper, motor_cfg, is_stub=False)
    link = yahboom_cfg.port.strip() or "ch340-libusb"
    print(f"drive: chassis → Yahboom USB ({link}) set_car_motion")
    return MotionStackBundle(client=client, yahboom_board=board)

  def _wrap_wheels(
    self, driver, motor_cfg: MotorConfig, *, is_stub: bool,
  ) -> RoverMotionClient:
    mixer = MecanumMixer(max_setpoint=motor_cfg.max_setpoint)
    odometry = EncoderOdometry(motor_cfg)
    motion = MotionController(
      mixer, odometry, motor_cfg, wheel_driver=driver,
    )
    return self._finish(motion, is_stub=is_stub)

  def _wrap_chassis(
    self,
    board: YahboomDriveBoard,
    mapper: DriveCommandChassisMapper,
    motor_cfg: MotorConfig,
    *,
    is_stub: bool,
  ) -> RoverMotionClient:
    mixer = MecanumMixer(max_setpoint=motor_cfg.max_setpoint)
    odometry = EncoderOdometry(motor_cfg)
    motion = MotionController(
      mixer,
      odometry,
      motor_cfg,
      chassis_driver=board,
      chassis_mapper=mapper,
    )
    return self._finish(motion, is_stub=is_stub)

  def _finish(self, motion: MotionController, *, is_stub: bool) -> RoverMotionClient:
    client = RoverMotionClient(motion, is_stub=is_stub)
    try:
      motion.initialize(settle_s=0.0)
    except Exception as exc:
      print(f"motion init: {exc}")
      client.note_i2c_error(str(exc))
    return client
