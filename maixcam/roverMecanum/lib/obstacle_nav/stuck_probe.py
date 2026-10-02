"""Live stuck-detector probe for TCP / SSH logs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StuckProbe:
  """One-line debug snapshot of the stuck analyzer."""

  ready: bool
  accel_valid: bool
  a_long: float
  a_lat: float
  bout_max_a: float
  bout_delta_v: float
  bout_enc: int
  bout_ms: int
  cmd_forward: int
  cmd_strafe: int
  level: str
  side: str
  detail: str

  def log_line(self) -> str:
    """Human-readable line for TCP clients / SSH."""
    valid = "aOK" if self.accel_valid else "a--"
    ready = "rdy" if self.ready else "off"
    return (
      f"stk {ready} {valid}"
      f" a={self.a_long:+.2f}/{self.a_lat:+.2f}"
      f" max={self.bout_max_a:.2f}"
      f" dv={self.bout_delta_v:+.2f}"
      f" enc={self.bout_enc}"
      f" cmd={self.cmd_forward}/{self.cmd_strafe}"
      f" {self.level}/{self.side}"
      f" {self.detail}".rstrip()
    )
