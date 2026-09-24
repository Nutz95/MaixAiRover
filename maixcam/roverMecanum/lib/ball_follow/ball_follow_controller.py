"""Thread-safe bridge between camera frames, ball policy, and HUD state."""

import threading
from time import monotonic

from lib.ball_follow.ball_detector import BallDetector
from lib.ball_follow.ball_follow_command import BallFollowCommand
from lib.ball_follow.ball_follow_policy import BallFollowPolicy
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_follow_snapshot import BallFollowSnapshot


class BallFollowController:
  """Own ball-follow mode and publish only typed observations and commands."""

  def __init__(self, settings: BallFollowSettings):
    """Create the detector/policy pair in manual mode."""
    self._lock = threading.Lock()
    self._settings = settings
    self._detector = BallDetector(settings)
    self._policy = BallFollowPolicy(settings)
    self._enabled = False
    self._color = settings.default_color
    self._observation = None
    self._trajectory = []
    self._command = BallFollowCommand(reason="manual")

  @property
  def enabled(self) -> bool:
    """Return whether automatic ball-follow mode is active."""
    with self._lock:
      return self._enabled

  @property
  def color(self) -> str:
    """Return the active blob color preset name."""
    with self._lock:
      return self._color

  def set_enabled(self, enabled: bool) -> None:
    """Enable or disable automatic mode and reset its safety state."""
    with self._lock:
      self._enabled = enabled
      self._policy.reset()
      self._observation = None
      self._trajectory.clear()
      self._command = BallFollowCommand(
        reason="enabled" if enabled else "manual",
      )

  def cycle_color(self) -> str:
    """Switch green/red LAB presets and clear the current track."""
    with self._lock:
      self._color = self._settings.next_color(self._color)
      self._policy.reset()
      self._observation = None
      self._trajectory.clear()
      self._command = BallFollowCommand(reason="color_changed")
      return self._color

  def apply_settings(self, settings: BallFollowSettings) -> None:
    """Replace detection/policy tuning after a config reload."""
    with self._lock:
      self._settings = settings
      self._detector = BallDetector(settings)
      self._policy = BallFollowPolicy(settings)
      if self._color not in settings.color_presets:
        self._color = settings.default_color
      self._observation = None
      self._trajectory.clear()
      self._command = BallFollowCommand(reason="settings_reloaded")

  def update(
    self,
    frame,
    yaw_deg=None,
    encoder_yaw_delta_deg=None,
  ) -> BallFollowCommand:
    """Detect the latest frame and return one safe automatic command."""
    with self._lock:
      if not self._enabled:
        self._command = BallFollowCommand(reason="manual")
        return self._command
      detector = self._detector
      policy = self._policy
      thresholds = self._settings.thresholds_for(self._color)
    now_ms = int(monotonic() * 1000)
    try:
      observation = detector.detect(frame, now_ms, thresholds)
    except Exception as detect_error:
      print(f"ball: detection failed: {detect_error}")
      observation = None
    command = policy.decide(
      observation,
      now_ms,
      yaw_deg=yaw_deg,
      encoder_yaw_delta_deg=encoder_yaw_delta_deg,
    )
    with self._lock:
      self._observation = observation
      if observation is not None:
        self._trajectory.append(observation)
        del self._trajectory[:-self._settings.trajectory_max_points]
      self._command = command
    return command

  def snapshot(self) -> BallFollowSnapshot:
    """Return a consistent mode/observation/command snapshot for the HUD."""
    with self._lock:
      return BallFollowSnapshot(
        enabled=self._enabled,
        color=self._color,
        observation=self._observation,
        trajectory=list(self._trajectory),
        command=self._command,
      )
