"""
MaixVision / packaged app entry point — Xbox controller -> Mecanum rover (Hiwonder I2C).

Packaged install: /maixapp/apps/maix_ai_rover/
MaixVision dev + deploy script: optional override from /root/roverMecanum/
"""

import os
import sys

_APP_ROOT = os.path.dirname(os.path.abspath(__file__))
_DEPLOY_ROOT = "/root/roverMecanum"

if _APP_ROOT not in sys.path:
  sys.path.insert(0, _APP_ROOT)

if (
  os.path.isdir(os.path.join(_DEPLOY_ROOT, "lib"))
  and _DEPLOY_ROOT not in sys.path
):
  sys.path.insert(0, _DEPLOY_ROOT)

from lib.xbox_rover_app import XboxRoverApp


def main():
  """Run the Xbox rover application until exit."""
  app_instance = XboxRoverApp()
  try:
    app_instance.run()
  finally:
    app_instance.shutdown()


if __name__ == "__main__":
  try:
    main()
  except Exception:
    import gc
    import traceback

    from maix import app, display, image, time

    msg = traceback.format_exc()
    print(msg)
    try:
      disp = display.Display()
      img = image.Image(disp.width(), disp.height(), bg=image.COLOR_BLACK)
      img.draw_string(0, 0, msg, image.COLOR_WHITE, scale=1.2)
      disp.show(img)
      while not app.need_exit():
        time.sleep_ms(100)
    except Exception:
      pass
    gc.collect()
