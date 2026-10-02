"""Post-IMU step: propose ground_top from depth floor wash, confirm with A."""

from __future__ import annotations

from lib.obstacle_nav.depth_ground_calib_step import DepthGroundCalibStep
from lib.obstacle_nav.ground_split_estimator import GroundSplitEstimator


class DepthGroundCalib:
  """Propose a green-band split; user nudges with stick then confirms."""

  MIN_RATIO = 0.28
  MAX_RATIO = 0.82

  def __init__(self) -> None:
    """Create an idle ground-split calib."""
    self._step = DepthGroundCalibStep.IDLE
    self._proposed_ratio: float | None = None
    self._estimator = GroundSplitEstimator()

  def is_active(self) -> bool:
    """True while waiting for depth or awaiting confirm."""
    return self._step in (
      DepthGroundCalibStep.WAIT_DEPTH,
      DepthGroundCalibStep.PROPOSE,
    )

  def uses_camera(self) -> bool:
    """True when the live camera HUD should stay visible."""
    return self.is_active()

  def show_depth(self) -> bool:
    """True when calib should force turbo depth on the HUD."""
    return self.is_active()

  def proposed_ratio(self) -> float | None:
    """Return the pending ground_top_ratio, if any."""
    return self._proposed_ratio

  def start(self, seed_ratio: float = 0.50) -> None:
    """Begin waiting for a depth frame; seed a stick-editable line."""
    self._step = DepthGroundCalibStep.WAIT_DEPTH
    self._proposed_ratio = self._clamp(seed_ratio)

  def reset(self) -> None:
    """Return to idle."""
    self._step = DepthGroundCalibStep.IDLE
    self._proposed_ratio = None

  def note_depth(
    self,
    depth_img,
    *,
    frame_width: int,
    frame_height: int,
    floor_warmth: float,
  ) -> None:
    """When waiting, snap to the light-green band (once); stick can refine."""
    if self._step != DepthGroundCalibStep.WAIT_DEPTH:
      return
    if depth_img is None:
      return
    ratio = self._estimator.propose(
      depth_img,
      frame_width=frame_width,
      frame_height=frame_height,
      floor_warmth=floor_warmth,
    )
    if ratio is None:
      # Stay editable on seed — depth may still be warming up.
      self._step = DepthGroundCalibStep.PROPOSE
      print(
        f"obstacle: ground split seed {self._proposed_ratio:.2f} (no green peak)"
      )
      return
    self._proposed_ratio = self._clamp(ratio)
    self._step = DepthGroundCalibStep.PROPOSE
    print(f"obstacle: ground split propose green {self._proposed_ratio:.2f}")

  def nudge(self, delta_ratio: float) -> None:
    """Move the proposed line (negative delta = higher on screen)."""
    if self._proposed_ratio is None:
      return
    if self._step == DepthGroundCalibStep.WAIT_DEPTH:
      self._step = DepthGroundCalibStep.PROPOSE
    self._proposed_ratio = self._clamp(self._proposed_ratio + delta_ratio)

  def confirm(self) -> float | None:
    """Accept proposal; return ratio or None if not ready."""
    if self._proposed_ratio is None:
      return None
    if self._step not in (
      DepthGroundCalibStep.PROPOSE,
      DepthGroundCalibStep.WAIT_DEPTH,
    ):
      return None
    ratio = self._proposed_ratio
    self._step = DepthGroundCalibStep.DONE
    self._proposed_ratio = None
    return ratio

  def skip(self) -> None:
    """Keep existing ground_top_ratio."""
    if not self.is_active():
      return
    self._step = DepthGroundCalibStep.SKIPPED
    self._proposed_ratio = None
    print("obstacle: ground split skipped")

  def prompt(self) -> str:
    """Short HUD line for the current step."""
    if self._proposed_ratio is None:
      return "GROUND CALIB: waiting depth…"
    return (
      f"GROUND {self._proposed_ratio:.2f}  "
      f"stick Y=move  A=OK  Skip=keep"
    )

  @classmethod
  def _clamp(cls, ratio: float) -> float:
    return max(cls.MIN_RATIO, min(cls.MAX_RATIO, float(ratio)))
