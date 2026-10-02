"""Severity of wheel-vs-body mismatch."""

from enum import Enum


class StuckLevel(Enum):
  """Progressive stuck indication for HUD and future maneuvers."""

  OK = "ok"
  WARN = "warn"
  STUCK = "stuck"
