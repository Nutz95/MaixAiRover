"""Read current evdev ABS axis state via Linux EVIOCGABS ioctl."""

import array
import fcntl
import struct

from lib.input.abs_info import AbsInfo

# struct input_absinfo { value, minimum, maximum, fuzz, flat, resolution }
_ABSINFO_FMT = "iiiiii"
_ABSINFO_SIZE = struct.calcsize(_ABSINFO_FMT)


def _eviocgabs_request(axis_code):
  """Build EVIOCGABS(axis) ioctl request number (Linux input.h)."""
  return (2 << 30) | (_ABSINFO_SIZE << 16) | (ord("E") << 8) | (0x40 + axis_code)


def read_absinfo(fd, axis_code):
  """
  Read kernel ABS state for one axis.

  Returns AbsInfo or None if ioctl unsupported.
  """
  if fd is None:
    return None
  fileno = fd.fileno() if hasattr(fd, "fileno") else fd
  buf = array.array("i", [0] * 6)
  try:
    fcntl.ioctl(fileno, _eviocgabs_request(axis_code), buf, True)
    return AbsInfo(value=buf[0], minimum=buf[1], maximum=buf[2], flat=buf[4])
  except OSError as ioctl_error:
    print(f"evdev: EVIOCGABS({axis_code}): {ioctl_error}")
    return None
