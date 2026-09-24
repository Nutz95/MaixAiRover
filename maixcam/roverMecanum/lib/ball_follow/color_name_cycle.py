"""Ordered color names for Menu/Start cycling (no tuple DTO)."""

from __future__ import annotations


class ColorNameCycle:
  """Cycle through configured ball color names."""

  def __init__(self, names: list[str]) -> None:
    """Store ordered unique non-empty names."""
    cleaned: list[str] = []
    for name in names:
      key = str(name).strip().lower()
      if key and key not in cleaned:
        cleaned.append(key)
    if not cleaned:
      raise ValueError("ColorNameCycle requires at least one color name")
    self._names = cleaned

  def first(self) -> str:
    """Return the first color in the cycle."""
    return self._names[0]

  def contains(self, name: str) -> bool:
    """Return True when ``name`` is in the cycle."""
    return name in self._names

  def next_after(self, color: str) -> str:
    """Return the next color after ``color``, or the first if unknown."""
    if color not in self._names:
      return self._names[0]
    index = self._names.index(color)
    return self._names[(index + 1) % len(self._names)]
