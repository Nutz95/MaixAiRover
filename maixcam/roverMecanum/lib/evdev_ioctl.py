"""Read current evdev ABS axis state via Linux EVIOCGABS ioctl."""

import array
import fcntl
import struct

# struct input_absinfo { value, minimum, maximum, fuzz, flat, resolution }
_ABSINFO_FMT = "iiiiii"
_ABSINFO_SIZE = struct.calcsize(_ABSINFO_FMT)


def _eviocgabs_request(axis_code):
  """Build EVIOCGABS(axis) ioctl request number (Linux input.h)."""
  return (2 << 30) | (_ABSINFO_SIZE << 16) | (ord("E") << 8) | (0x40 + axis_code)


def read_absinfo(fd, axis_code):
  """
  Read kernel ABS state for one axis.

  Returns (value, minimum, maximum, flat) or None if ioctl unsupported.
  """
  if fd is None:
    return None
  fileno = fd.fileno() if hasattr(fd, "fileno") else fd
  buf = array.array("i", [0] * 6)
  try:
    fcntl.ioctl(fileno, _eviocgabs_request(axis_code), buf, True)
    return int(buf[0]), int(buf[1]), int(buf[2]), int(buf[4])
  except OSError:
    return None
