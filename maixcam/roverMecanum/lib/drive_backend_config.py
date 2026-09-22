"""Top-level motion backend selection from config root."""

from __future__ import annotations

from dataclasses import dataclass

from lib.drive_backend_kind import DriveBackendKind
from lib.yahboom_config import YahboomConfig


@dataclass(frozen=True)
class DriveBackendConfig:
  """Resolved ``drive_backend`` + typed Yahboom settings."""

  kind: DriveBackendKind
  yahboom: YahboomConfig

  @classmethod
  def from_root(cls, root: dict) -> "DriveBackendConfig":
    """Parse ``drive_backend`` + ``yahboom`` from the loaded config root."""
    raw = str(root.get("drive_backend", DriveBackendKind.ESP.value)).strip().lower()
    try:
      kind = DriveBackendKind(raw)
    except ValueError as exc:
      allowed = ", ".join(k.value for k in DriveBackendKind)
      raise ValueError(
        f"drive_backend={raw!r} invalid; expected one of: {allowed}"
      ) from exc
    yah_raw = root.get("yahboom", {})
    yahboom = YahboomConfig.from_mapping(yah_raw if isinstance(yah_raw, dict) else {})
    return cls(kind=kind, yahboom=yahboom)
