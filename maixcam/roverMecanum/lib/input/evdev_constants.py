"""
Linux evdev type/code constants for Xbox controllers.

These match <linux/input-event-codes.h>. We use them when parsing
/dev/input/event* binary records from BlueZ HID devices.
"""

# --- Event types -----------------------------------------------------------

EV_SYN = 0x00   # Synchronization event (end of a report)
EV_KEY = 0x01   # Digital button press/release
EV_ABS = 0x03   # Absolute axis (sticks, triggers, hat)

# SYN_REPORT marks the end of one hardware input report.
SYN_REPORT = 0

# --- Absolute axis codes (ABS_*) -------------------------------------------

ABS_X = 0x00      # Left stick horizontal
ABS_Y = 0x01      # Left stick vertical
ABS_Z = 0x02      # Often left trigger (layout-dependent)
ABS_RX = 0x03     # Right stick horizontal
ABS_RY = 0x04     # Right stick vertical
ABS_RZ = 0x05     # Often right trigger (layout-dependent)
ABS_HAT0X = 0x10  # D-pad horizontal (-1, 0, +1)
ABS_HAT0Y = 0x11  # D-pad vertical (-1, 0, +1)
ABS_GAS = 0x09    # Accelerator / RT on some drivers
ABS_BRAKE = 0x0A  # Brake / LT on some drivers

# Normalized stick range sent to the mapping engine.
AXIS_MAX = 32767

# Microsoft USB vendor id (045e) — used to spot Xbox pads in /sys.
XBOX_VENDOR_ID = "045e"

# Default ABS ranges when sysfs/ioctl metadata is unavailable.
# ABS_Z / ABS_RZ are layout-dependent (stick on maixcam_bt, trigger on USB
# standard) — never assume trigger here; callers pass prefer_trigger.
_ALWAYS_TRIGGER_CODES = frozenset({ABS_GAS, ABS_BRAKE})


def default_abs_range(axis_code, prefer_trigger=False):
  """Fallback min/max/flat when the kernel absinfo is missing."""
  if prefer_trigger or axis_code in _ALWAYS_TRIGGER_CODES:
    return 0, 1023, 64
  return 0, 65535, 4096

# --- Button codes (BTN_*) --------------------------------------------------

BTN_A = 0x130
BTN_B = 0x131
BTN_X = 0x133
BTN_Y = 0x134
BTN_TL = 0x136       # Left bumper (LB)
BTN_TR = 0x137       # Right bumper (RB)
BTN_TL2 = 0x138      # Left trigger as digital button (some BT stacks)
BTN_TR2 = 0x139      # Right trigger as digital button
BTN_THUMBL = 0x13C   # Alternate LB code on some Xbox BT drivers
BTN_THUMBR = 0x13D   # Alternate RB code on some Xbox BT drivers
BTN_SELECT = 0x13A
BTN_START = 0x13B

# Linux input framework D-pad buttons (alternative to ABS_HAT0X/Y).
BTN_DPAD_UP = 0x220
BTN_DPAD_DOWN = 0x221
BTN_DPAD_LEFT = 0x222
BTN_DPAD_RIGHT = 0x223
