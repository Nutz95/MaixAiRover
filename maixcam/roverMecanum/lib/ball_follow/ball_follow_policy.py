"""Sequential visual policy for approaching a colored ball safely."""

from typing import Optional

from lib.ball_follow.ball_follow_command import BallFollowCommand
from lib.ball_follow.ball_follow_settings import BallFollowSettings
from lib.ball_follow.ball_observation import BallObservation

_PHASE_TRACK = "track"
_PHASE_LOST_WAIT = "lost_wait"
_PHASE_SEARCH_SPIN = "search_spin"
_PHASE_COMPASS_FIX = "compass_fix"
_PHASE_SEARCH_PAUSE = "search_pause"
_PHASE_RETREAT = "retreat"


class BallFollowPolicy:
  """Keep the ball in a stable image band — that *is* following.

  Strategy (visual formation):
  1. Spin from **image X error only** (no image-velocity feedforward — ego
     rotation poisons blob motion while turning and caused spin pump).
     Authority rises toward the frame edge; blob **height** scales urgency
     (close/large → stronger yaw, far/small → milder — same bearing, but
     near balls cross the FOV faster).
  2. Y setpoint at mid-frame: high → approach, low → retreat, in-band → stop.
  3. Image X velocity is updated only while we are *not* spinning, and used
     solely to pick search direction when the ball leaves the frame.
  4. Blob height / hard bottom edge are safety reverse only.

  Lost-ball search: retreat first → ~360° spin (IMU / encoders) → compass
  fix → pause → retreat → spin…
  """

  def __init__(self, settings: BallFollowSettings):
    """Create a stateful policy with loss timing and search phases."""
    self._settings = settings
    self._last_observation = None
    self._last_seen_ms = None
    self._velocity_x = 0.0
    self._last_spin_command = 0
    self._phase = _PHASE_TRACK
    self._phase_started_ms = None
    self._search_spin_sign = 1
    self._pause_next = _PHASE_RETREAT
    self._encoder_yaw_accum = 0.0
    self._imu_yaw_accum = 0.0
    self._search_heading_start = None
    self._last_search_yaw = None
    self._holding_distance = False

  def reset(self) -> None:
    """Forget the target and force the next decision to stop safely."""
    self._last_observation = None
    self._last_seen_ms = None
    self._velocity_x = 0.0
    self._last_spin_command = 0
    self._phase = _PHASE_TRACK
    self._phase_started_ms = None
    self._search_spin_sign = 1
    self._pause_next = _PHASE_RETREAT
    self._encoder_yaw_accum = 0.0
    self._imu_yaw_accum = 0.0
    self._search_heading_start = None
    self._last_search_yaw = None
    self._holding_distance = False

  def decide(
    self,
    observation: Optional[BallObservation],
    now_ms: int,
    yaw_deg: Optional[float] = None,
    encoder_yaw_delta_deg: Optional[float] = None,
  ) -> BallFollowCommand:
    """Return one bounded command for the current observation or loss state."""
    if observation is None:
      return self._lost_command(now_ms, yaw_deg, encoder_yaw_delta_deg)

    self._phase = _PHASE_TRACK
    self._phase_started_ms = None
    self._encoder_yaw_accum = 0.0
    self._imu_yaw_accum = 0.0
    self._search_heading_start = None
    self._last_search_yaw = None
    # Image velocity is only trustworthy while the chassis is not yawing.
    if self._last_spin_command == 0:
      self._update_velocity_x(observation)
    self._last_observation = observation
    self._last_seen_ms = observation.timestamp_ms

    horizontal_error = observation.x_ratio - self._settings.image_center_x_ratio
    height = observation.height_ratio
    y_ratio = observation.y_ratio

    # Oversized blob or hard bumper — reverse even while off-center.
    if height >= self._settings.too_close_height_ratio or (
      y_ratio >= self._settings.too_close_center_y_ratio
    ):
      self._holding_distance = False
      self._last_spin_command = 0
      return self._retreat_command_y(y_ratio)

    spin = 0
    if abs(horizontal_error) > self._settings.horizontal_deadzone:
      spin = self._align_spin(horizontal_error, height)

    forward, reason = self._y_distance_axes(y_ratio)
    if spin != 0 and reason == "target_distance":
      reason = "align"
    elif spin != 0 and reason == "approach":
      reason = "align"
    self._last_spin_command = spin
    return BallFollowCommand(
      forward=forward,
      spin=spin,
      reason=reason,
    )

  def _y_band(self) -> tuple[float, float, float, float]:
    """Return enter_lo, enter_hi, exit_lo, exit_hi for the Y hold band."""
    target = self._settings.target_center_y_ratio
    tol = self._settings.target_y_tolerance_ratio
    return (
      target - tol,
      target + tol,
      target - 2.0 * tol,
      target + 2.0 * tol,
    )

  def _y_distance_axes(self, y_ratio: float) -> tuple[int, str]:
    """Servo on image Y: high→approach, low→retreat, in-band→stop."""
    enter_lo, enter_hi, exit_lo, exit_hi = self._y_band()
    if self._holding_distance:
      if exit_lo <= y_ratio <= exit_hi:
        return 0, "target_distance"
      self._holding_distance = False

    if y_ratio < enter_lo:
      axis = self._approach_axis_y(y_ratio)
      return self._settings.forward_axis_sign * axis, "approach"
    if y_ratio > enter_hi:
      axis = self._retreat_axis_y(y_ratio)
      return -self._settings.forward_axis_sign * axis, "too_close"

    self._holding_distance = True
    return 0, "target_distance"

  def _align_spin(self, horizontal_error: float, height_ratio: float) -> int:
    """Proportional spin from X error; height scales urgency (close → faster).

    ``align_spin_curve`` is the power on normalized error ``t = (err/full)^curve``:
    - ``curve < 1`` (e.g. 0.55): firm just outside the deadzone (catch crosses).
    - ``curve = 1``: linear ceiling ramp.
    - ``curve > 1``: soft near center (old ease-in — lagged on center passes).
    """
    err = abs(horizontal_error)
    full = max(1e-6, self._settings.align_spin_full_error)
    curve = max(0.2, min(3.0, self._settings.align_spin_curve))
    t = min(1.0, err / full) ** curve
    size_scale = self._align_size_scale(height_ratio)
    span = self._settings.max_spin_axis - self._settings.min_spin_axis
    base_ceiling = self._settings.min_spin_axis + t * span
    ceiling = max(1, min(
      self._settings.max_spin_axis,
      int(base_ceiling * size_scale),
    ))
    raw = int(horizontal_error * self._settings.spin_gain * size_scale)
    magnitude = min(ceiling, abs(raw))
    if magnitude <= 0:
      return 0
    # Soft floor once authority is already on — not a near-center bang kick.
    if t >= 0.25:
      magnitude = max(self._settings.min_spin_axis, magnitude)
    sign = 1 if horizontal_error > 0 else -1
    return self._settings.spin_axis_sign * sign * magnitude

  def _align_size_scale(self, height_ratio: float) -> float:
    """Map blob height to spin urgency: far < 1, formation ≈ 1, close > 1.

    Bearing for a given X error does not depend on distance, but a near ball
    sweeps the FOV faster in image space — so we yaw harder when large.
    """
    ref = max(0.05, self._settings.target_height_ratio)
    # ponytail: linear in height/ref; upgrade = true range from depth/diameter.
    return max(0.75, min(1.55, height_ratio / ref))

  def _retreat_command_y(self, y_ratio: float) -> BallFollowCommand:
    """Reverse from Y error (or emergency bumper)."""
    return BallFollowCommand(
      forward=-self._settings.forward_axis_sign * self._retreat_axis_y(y_ratio),
      reason="too_close",
    )

  def _approach_axis_y(self, y_ratio: float) -> int:
    """Forward magnitude from how high the ball sits above the Y setpoint."""
    target = self._settings.target_center_y_ratio
    error = max(self._settings.min_distance_error, target - y_ratio)
    axis = self._distance_axis(
      error,
      self._settings.min_forward_axis,
      self._settings.max_forward_axis,
      max(self._settings.approach_full_error_floor, target),
      curve=self._settings.approach_curve,
    )
    enter_lo, _, _, _ = self._y_band()
    # Soft near the band so we settle instead of slamming through.
    if y_ratio >= enter_lo - self._settings.target_y_tolerance_ratio:
      soft_cap = max(
        self._settings.min_forward_axis,
        int(self._settings.max_forward_axis * self._settings.approach_near_cap_ratio),
      )
      axis = min(axis, soft_cap)
    return axis

  def _retreat_axis_y(self, y_ratio: float) -> int:
    """Reverse magnitude from how far below the Y setpoint the ball sits."""
    target = self._settings.target_center_y_ratio
    error = max(self._settings.min_distance_error, y_ratio - target)
    soft_max = max(
      self._settings.min_forward_axis,
      int(self._settings.max_retreat_axis * self._settings.retreat_soft_cap_ratio),
    )
    full_error = max(
      self._settings.approach_full_error_floor,
      self._settings.too_close_center_y_ratio - target,
    )
    return self._distance_axis(
      error,
      max(1, self._settings.min_forward_axis // 2),
      soft_max,
      full_error,
      curve=self._settings.retreat_curve,
    )

  def _update_velocity_x(self, observation: BallObservation) -> None:
    if self._last_observation is None:
      self._velocity_x = 0.0
      return
    elapsed_ms = observation.timestamp_ms - self._last_observation.timestamp_ms
    if elapsed_ms <= 0 or elapsed_ms > self._settings.velocity_timeout_ms:
      self._velocity_x = 0.0
      return
    self._velocity_x = (
      observation.x_ratio - self._last_observation.x_ratio
    ) / (elapsed_ms / 1000.0)

  def _lost_command(
    self,
    now_ms: int,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> BallFollowCommand:
    if self._last_seen_ms is None:
      return BallFollowCommand(reason="no_target")

    if self._phase == _PHASE_TRACK:
      self._enter_phase(_PHASE_LOST_WAIT, now_ms)
      self._search_spin_sign = self._exit_direction_sign()

    handlers = {
      _PHASE_LOST_WAIT: self._phase_lost_wait,
      _PHASE_SEARCH_SPIN: self._phase_search_spin,
      _PHASE_COMPASS_FIX: self._phase_compass_fix,
      _PHASE_SEARCH_PAUSE: self._phase_search_pause,
      _PHASE_RETREAT: self._phase_retreat,
    }
    handler = handlers.get(self._phase)
    if handler is None:
      return BallFollowCommand(reason="target_lost")
    return handler(now_ms, yaw_deg, encoder_yaw_delta_deg)

  def _lost_exited_bottom(self) -> bool:
    """Last sighting was at/below the Y setpoint — reverse without waiting."""
    obs = self._last_observation
    if obs is None:
      return False
    return obs.y_ratio >= self._settings.target_center_y_ratio

  def _phase_lost_wait(
    self,
    now_ms: int,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> BallFollowCommand:
    del encoder_yaw_delta_deg
    # Bottom exit: reverse immediately (no lost_search_ms dead time).
    if (
      not self._lost_exited_bottom()
      and now_ms - self._last_seen_ms < self._settings.lost_search_ms
    ):
      return BallFollowCommand(reason="target_lost")
    # Retreat first (often under/near bumper), then spin — skips a useless cycle.
    self._pause_next = _PHASE_SEARCH_SPIN
    self._enter_phase(_PHASE_RETREAT, now_ms)
    return self._phase_retreat(now_ms, yaw_deg, None)

  def _accumulate_search_yaw(
    self,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> None:
    """Integrate relative yaw; prefer board IMU, clamp encoder glitches."""
    if yaw_deg is not None:
      if self._last_search_yaw is not None:
        step = abs(self.yaw_delta_deg(self._last_search_yaw, yaw_deg))
        if step < self._settings.search_imu_glitch_deg:
          self._imu_yaw_accum += step
      self._last_search_yaw = yaw_deg
    if encoder_yaw_delta_deg is not None:
      self._encoder_yaw_accum += min(
        self._settings.search_encoder_yaw_cap_deg, abs(encoder_yaw_delta_deg),
      )

  def _search_spin_done(self, now_ms: int) -> bool:
    """Finish search spin by IMU (preferred) or encoder yaw, else timed stall."""
    elapsed_ms = now_ms - self._phase_started_ms
    target = self._settings.search_turn_deg
    if target > 0:
      if self._imu_yaw_accum >= target:
        return True
      if self._imu_yaw_accum <= 1.0 and self._encoder_yaw_accum >= target:
        return True
    stall_ms = self._settings.search_turn_ms * self._settings.search_turn_stall_mult
    return elapsed_ms >= stall_ms

  def _phase_search_spin(
    self,
    now_ms: int,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> BallFollowCommand:
    self._accumulate_search_yaw(yaw_deg, encoder_yaw_delta_deg)
    if not self._search_spin_done(now_ms):
      return BallFollowCommand(
        spin=self._search_spin_sign * self._settings.search_spin_axis,
        reason="search",
      )
    self._enter_phase(_PHASE_COMPASS_FIX, now_ms)
    return self._phase_compass_fix(now_ms, yaw_deg, None)

  def _enter_search_spin(self, now_ms: int, yaw_deg: Optional[float]) -> None:
    self._enter_phase(_PHASE_SEARCH_SPIN, now_ms)
    self._encoder_yaw_accum = 0.0
    self._imu_yaw_accum = 0.0
    self._search_heading_start = yaw_deg
    self._last_search_yaw = yaw_deg

  def _phase_compass_fix(
    self,
    now_ms: int,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> BallFollowCommand:
    del encoder_yaw_delta_deg
    elapsed_ms = now_ms - self._phase_started_ms
    timeout = elapsed_ms >= self._settings.compass_fix_timeout_ms
    target = self._search_heading_start
    if target is None or yaw_deg is None:
      self._pause_next = _PHASE_RETREAT
      self._enter_phase(_PHASE_SEARCH_PAUSE, now_ms)
      return BallFollowCommand(reason="search_pause")
    error = self.yaw_delta_deg(yaw_deg, target)
    if abs(error) <= self._settings.compass_fix_tolerance_deg or timeout:
      self._pause_next = _PHASE_RETREAT
      self._enter_phase(_PHASE_SEARCH_PAUSE, now_ms)
      return BallFollowCommand(reason="search_pause")
    # error > 0 ⇒ need CCW (teleop −spin); Yahboom mapper flips spin → −vz.
    spin_sign = -1 if error > 0 else 1
    return BallFollowCommand(
      spin=spin_sign * self._settings.compass_fix_spin_axis,
      reason="compass_fix",
    )

  def _phase_search_pause(
    self,
    now_ms: int,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> BallFollowCommand:
    del encoder_yaw_delta_deg
    if now_ms - self._phase_started_ms < self._settings.search_pause_ms:
      return BallFollowCommand(reason="search_pause")
    nxt = self._pause_next
    if nxt == _PHASE_SEARCH_SPIN:
      self._enter_search_spin(now_ms, yaw_deg)
      return self._phase_search_spin(now_ms, yaw_deg, 0.0)
    self._enter_phase(_PHASE_RETREAT, now_ms)
    return self._phase_retreat(now_ms, yaw_deg, None)

  def _phase_retreat(
    self,
    now_ms: int,
    yaw_deg: Optional[float],
    encoder_yaw_delta_deg: Optional[float],
  ) -> BallFollowCommand:
    del yaw_deg, encoder_yaw_delta_deg
    if now_ms - self._phase_started_ms < self._settings.search_retreat_ms:
      return BallFollowCommand(
        forward=-self._settings.forward_axis_sign * self._settings.search_retreat_axis,
        reason="search_retreat",
      )
    self._pause_next = _PHASE_SEARCH_SPIN
    self._enter_phase(_PHASE_SEARCH_PAUSE, now_ms)
    return BallFollowCommand(reason="search_pause")

  def _enter_phase(self, phase: str, now_ms: int) -> None:
    self._phase = phase
    self._phase_started_ms = now_ms

  def _exit_direction_sign(self) -> int:
    """Search spin from last free-motion velocity, else last image side."""
    center = self._settings.image_center_x_ratio
    if abs(self._velocity_x) >= self._settings.exit_velocity_threshold:
      direction = 1 if self._velocity_x > 0 else -1
    elif self._last_observation is not None:
      direction = 1 if self._last_observation.x_ratio >= center else -1
    else:
      direction = 1
    return self._settings.spin_axis_sign * direction

  def _distance_axis(
    self,
    error: float,
    hard_floor: int,
    hard_max: int,
    full_error: float,
    curve: float = 1.0,
  ) -> int:
    """Progressive approach/retreat magnitude from a distance error.

    ``curve < 1`` eases out (far → near-max sooner). ``curve > 1`` eases in
    (soft near target, firm only when error is large).
    """
    if full_error <= 0:
      t = 1.0
    else:
      t = max(0.0, min(1.0, abs(error) / full_error))
    if curve != 1.0:
      t = t ** curve
    floor, ceiling = self._progressive_limits(hard_floor, hard_max, t, 1.0)
    if error < self._settings.target_tolerance_ratio * 2:
      floor = 1
    gain_mag = abs(int(error * self._settings.forward_gain))
    # Gain alone under-drives far approach; take the progressive envelope too.
    prog_mag = int(floor + t * (ceiling - floor))
    magnitude = max(gain_mag, prog_mag)
    if magnitude <= 0:
      return 0
    return max(floor, min(ceiling, magnitude))

  @staticmethod
  def yaw_delta_deg(start_deg: float, now_deg: float) -> float:
    """Signed shortest yaw difference in degrees, in (-180, 180]."""
    return (now_deg - start_deg + 180.0) % 360.0 - 180.0

  @staticmethod
  def _progressive_limits(min_axis: int, max_axis: int, error: float, full_error: float):
    """Soft floor + ceiling from error size (gentle near goal, full when far)."""
    if max_axis <= min_axis:
      return min_axis, min_axis
    t = 1.0 if full_error <= 0 else max(0.0, min(1.0, abs(error) / full_error))
    # Encoded closed-loop: soft floor can be gentle (no open-loop deadband kick).
    floor = max(1, int(min_axis * (0.25 + 0.75 * t)))
    ceiling = max(floor, int(min_axis + t * (max_axis - min_axis)))
    return floor, ceiling

  @staticmethod
  def _drive_axis(value: float, min_axis: int, max_axis: int) -> int:
    """Linear vision→motor map with a breakaway floor (joystick uses expo instead)."""
    if value == 0:
      return 0
    sign = 1 if value > 0 else -1
    magnitude = min(max_axis, abs(int(value)))
    if magnitude > 0:
      magnitude = max(min_axis, magnitude)
    return sign * magnitude
