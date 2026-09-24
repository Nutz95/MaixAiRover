"""Stick response curves: linear, exponential, logarithmic."""

import math


def apply_curve(norm, curve, expo=1.0):
  """
  Map normalized stick magnitude [0..1] through a response curve.

  curve:
    "linear" — proportional
    "expo"   — power curve (expo > 1 = softer center)
    "log"    — logarithmic (fine control near center, full throw at edges)
  """
  norm = max(0.0, min(1.0, float(norm)))
  if norm <= 0.0:
    return 0.0
  key = (curve or "expo").strip().lower()
  if key == "linear":
    return norm
  if key == "expo":
    e = max(0.3, min(3.0, float(expo)))
    return norm ** e
  # default: gentle log (less aggressive than full log1p(9))
  return math.log1p(2.5 * norm) / math.log(3.5)
