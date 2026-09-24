"""Load ESP or Yahboom motion stack from config."""

from __future__ import annotations

from lib.app.drive_stack_handles import DriveStackHandles
from lib.esp.esp_debug_session import EspDebugSession
from lib.esp.esp_link_config import EspLinkConfig
from lib.motion.drive_backend_config import DriveBackendConfig
from lib.motion.drive_backend_kind import DriveBackendKind
from lib.motion.motion_stack_factory import MotionStackFactory
from lib.yahboom.yahboom_debug_session import YahboomDebugSession


class DriveStackLoader:
  """Build the teleop drive backend from ``config.json``."""

  def load(self, config: dict, esp_links: EspLinkConfig) -> DriveStackHandles:
    """Create Yahboom USB or dual ESP UART motion clients."""
    backend = DriveBackendConfig.from_root(config)
    if backend.kind is DriveBackendKind.YAHBOOM:
      bundle = MotionStackFactory().create_yahboom(config)
      print("drive_backend: yahboom (USB Rosmaster closed-loop)")
      return DriveStackHandles(
        kind=backend.kind,
        rover=bundle.client,
        yahboom_board=bundle.yahboom_board,
        yahboom_debug=YahboomDebugSession(bundle.yahboom_board),
        esp_front_debug=None,
        esp_rear_debug=None,
      )
    front = EspDebugSession(uart_port=esp_links.front.uart_port)
    rear = None
    set_rear = None
    if esp_links.rear is not None:
      rear = EspDebugSession(uart_port=esp_links.rear.uart_port)
      set_rear = rear.set_drive
    bundle = MotionStackFactory().create_esp(
      config,
      set_front_drive=front.set_drive,
      set_rear_drive=set_rear,
    )
    print("drive_backend: esp (Waveshare UART)")
    return DriveStackHandles(
      kind=backend.kind,
      rover=bundle.client,
      yahboom_board=None,
      yahboom_debug=None,
      esp_front_debug=front,
      esp_rear_debug=rear,
    )
