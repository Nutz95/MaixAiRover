"""DepthViewMode config parsing."""

from __future__ import annotations

from lib.vision.depth_view_mode import DepthViewMode


def test_depth_view_mode_parse() -> None:
  """Known aliases map; junk falls back to blend."""
  assert DepthViewMode.parse("blend") is DepthViewMode.BLEND
  assert DepthViewMode.parse("DEPTH") is DepthViewMode.DEPTH
  assert DepthViewMode.parse("rgb") is DepthViewMode.RGB
  assert DepthViewMode.parse("nope") is DepthViewMode.BLEND
  assert DepthViewMode.parse("nope", DepthViewMode.RGB) is DepthViewMode.RGB
