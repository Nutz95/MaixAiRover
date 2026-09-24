"""Host check: peripheral checklist formatting (no MaixPy)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum"))

from lib.health.peripheral_check import PeripheralCheck
from lib.health.peripheral_checklist import PeripheralChecklist


def main() -> None:
  """Assert checklist formatting for HUD/log lines."""
  report = PeripheralChecklist(
    checks=[
      PeripheralCheck(name="Xbox", ok=True, detail="HID connected"),
      PeripheralCheck(name="ESP UART", ok=False, detail="timeout"),
    ]
  )
  lines = report.log_lines()
  assert lines[0] == "[OK] Xbox: HID connected"
  assert lines[1] == "[FAIL] ESP UART: timeout"
  assert report.all_ok() is False
  print("peripheral_checklist: ok")


if __name__ == "__main__":
  main()
