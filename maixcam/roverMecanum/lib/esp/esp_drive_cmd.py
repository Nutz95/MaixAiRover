"""Queued FL/FR drive command for EspLinkPump."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EspDriveCmd:
  """Latest front-pair setpoint; ``stop`` selects STOP framing."""

  fl: int
  fr: int
  stop: bool = False
