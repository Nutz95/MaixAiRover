"""Installation paths on MaixCam (packaged app + optional deploy copy)."""

import os

# Optional deploy target (tools/deploy_rover_mecanum.ps1).
ROVER_MECANUM_ROOT = "/root/roverMecanum"

# App bundle root: parent of lib/ (works packaged and in MaixVision).
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_CONFIG_PATH = os.path.join(APP_ROOT, "config.json")


def resolve_config_path():
  """
  Pick the active config.json.

  Search order:
    1. config.json next to main.py (packaged app or MaixVision project)
    2. ./config.json relative to cwd
    3. /root/roverMecanum/config.json (deploy script copy)
  """
  candidates = (
    os.path.join(APP_ROOT, "config.json"),
    os.path.join(os.getcwd(), "config.json"),
    f"{ROVER_MECANUM_ROOT}/config.json",
  )
  for path in candidates:
    if os.path.isfile(path):
      return path
  return DEFAULT_CONFIG_PATH
