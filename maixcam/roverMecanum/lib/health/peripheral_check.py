"""One peripheral health line for the post-connect checklist."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PeripheralCheck:
  """Named OK/FAIL row shown after the Xbox pad connects."""

  name: str
  ok: bool
  detail: str

  def format_line(self) -> str:
    """Return a single log/HUD line for this check."""
    mark = "OK" if self.ok else "FAIL"
    return f"[{mark}] {self.name}: {self.detail}"
