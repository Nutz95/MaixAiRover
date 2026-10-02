"""Decode Maix Image.get_pixel into R,G,B (always request rgbtuple)."""

from __future__ import annotations


def pixel_rgb(img, x: int, y: int):
  """Return (r, g, b) or None if the pixel cannot be read as color."""
  x = max(0, min(img.width() - 1, x))
  y = max(0, min(img.height() - 1, y))
  try:
    # MaixCDK: rgbtuple=False returns [packed]; True returns [R,G,B].
    pixel = img.get_pixel(x, y, True)
  except TypeError:
    try:
      pixel = img.get_pixel(x, y)
    except Exception as pixel_error:
      print(f"depth pixel: {pixel_error}")
      return None
  except Exception as pixel_error:
    print(f"depth pixel: {pixel_error}")
    return None
  if isinstance(pixel, (tuple, list)):
    if len(pixel) >= 3:
      return int(pixel[0]), int(pixel[1]), int(pixel[2])
    if len(pixel) == 1:
      packed = int(pixel[0])
      return (packed >> 16) & 255, (packed >> 8) & 255, packed & 255
  if isinstance(pixel, int):
    return (pixel >> 16) & 255, (pixel >> 8) & 255, pixel & 255
  return None


def pixel_warmth(img, x: int, y: int) -> float:
  """Turbo colormap warmth (R−B)/255 — near = high."""
  rgb = pixel_rgb(img, x, y)
  if rgb is None:
    return 0.0
  return (rgb[0] - rgb[2]) / 255.0
