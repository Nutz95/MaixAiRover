"""Detect stuck / collision from IMU attitude + accel vs wheel encoders."""

from __future__ import annotations

from lib.obstacle_nav.chassis_accel import ChassisAccel
from lib.obstacle_nav.collision_side import CollisionSide
from lib.obstacle_nav.imu_chassis_frame import ImuChassisFrame
from lib.obstacle_nav.motion_probe_sample import MotionProbeSample
from lib.obstacle_nav.obstacle_nav_settings import ObstacleNavSettings
from lib.obstacle_nav.stuck_cause import StuckCause
from lib.obstacle_nav.stuck_level import StuckLevel
from lib.obstacle_nav.stuck_probe import StuckProbe
from lib.obstacle_nav.stuck_report import StuckReport


class StuckDetector:
  """Accumulate short motion windows and emit a StuckReport."""

  def __init__(self, settings: ObstacleNavSettings) -> None:
    """Create an idle detector with default chassis frame."""
    self._settings = settings
    self._frame = ImuChassisFrame.default()
    self._accel = ChassisAccel(self._frame)
    self._samples: list[MotionProbeSample] = []
    self._last = StuckReport.clear()
    self._bout_cmd = 0
    self._bout_kind = ""
    self._bout_started_ms = 0
    self._bout_last_ms = 0
    self._bout_max_abs_accel = 0.0
    self._bout_max_horizontal = 0.0
    self._bout_delta_v = 0.0
    self._bout_enc_start = 0
    self._last_a_long = 0.0
    self._last_a_lat = 0.0
    self._last_accel_valid = False
    self._impact_side = CollisionSide.NONE
    self._impact_since_ms: int | None = None

  def apply_settings(self, settings: ObstacleNavSettings) -> None:
    """Replace thresholds without clearing the frame."""
    self._settings = settings

  def set_frame(self, frame: ImuChassisFrame) -> None:
    """Install rest bias / sign map from the calib wizard."""
    self._frame = frame
    self._accel = ChassisAccel(frame)

  def frame(self) -> ImuChassisFrame:
    """Return the active chassis IMU frame."""
    return self._frame

  def reset(self) -> None:
    """Forget samples and report OK."""
    self._samples.clear()
    self._last = StuckReport.clear()
    self._bout_cmd = 0
    self._bout_kind = ""
    self._bout_started_ms = 0
    self._bout_last_ms = 0
    self._bout_max_abs_accel = 0.0
    self._bout_max_horizontal = 0.0
    self._bout_delta_v = 0.0
    self._bout_enc_start = 0
    self._last_a_long = 0.0
    self._last_a_lat = 0.0
    self._last_accel_valid = False
    self._impact_side = CollisionSide.NONE
    self._impact_since_ms = None

  def last_report(self) -> StuckReport:
    """Return the last computed report."""
    return self._last

  def probe(self, *, ready: bool) -> StuckProbe:
    """Return a debug snapshot of the current bout."""
    bout_ms = 0
    bout_enc = 0
    if self._bout_cmd != 0 and self._samples:
      newest = self._samples[-1]
      bout_ms = newest.timestamp_ms - self._bout_started_ms
      bout_enc = abs(newest.encoder_sum - self._bout_enc_start)
    return StuckProbe(
      ready=ready,
      accel_valid=self._last_accel_valid,
      a_long=self._last_a_long,
      a_lat=self._last_a_lat,
      bout_max_a=self._bout_max_abs_accel,
      bout_delta_v=self._bout_delta_v,
      bout_enc=bout_enc,
      bout_ms=bout_ms,
      cmd_forward=self._bout_cmd if self._bout_kind == "fwd" else 0,
      cmd_strafe=self._bout_cmd if self._bout_kind == "strafe" else 0,
      level=self._last.level.value,
      side=self._last.side.value,
      detail=self._last.detail,
    )

  def update(self, sample: MotionProbeSample) -> StuckReport:
    """Push one sample and recompute stuck level / side."""
    self._samples.append(sample)
    window = self._settings.stuck_window_ms
    cutoff = sample.timestamp_ms - window
    self._samples = [row for row in self._samples if row.timestamp_ms >= cutoff]
    if len(self._samples) < 2:
      self._last = StuckReport.clear()
      return self._last
    self._last = self._analyze(sample)
    return self._last

  def _analyze(self, newest: MotionProbeSample) -> StuckReport:
    cmd_forward = newest.axis_forward
    cmd_spin = newest.axis_spin
    cmd_strafe = newest.axis_strafe
    cmd_deadband = self._settings.cmd_axis_threshold
    moving_cmd = (
      abs(cmd_forward) > cmd_deadband
      or abs(cmd_spin) > cmd_deadband
      or abs(cmd_strafe) > cmd_deadband
    )

    a_long = self._accel.forward(newest.ax, newest.ay, newest.az)
    a_lat = self._accel.lateral(newest.ax, newest.ay, newest.az)
    horiz = self._accel.horizontal_peak(newest.ax, newest.ay, newest.az)
    abs_a = abs(a_long) if newest.accel_valid else 0.0
    abs_lat = abs(a_lat) if newest.accel_valid else 0.0
    self._last_a_long = a_long if newest.accel_valid else 0.0
    self._last_a_lat = a_lat if newest.accel_valid else 0.0
    self._last_accel_valid = newest.accel_valid

    pitch_delta = newest.pitch_deg - self._frame.pitch0_deg
    roll_delta = newest.roll_deg - self._frame.roll0_deg
    pitch_signed = pitch_delta * self._frame.pitch_forward_sign

    # Attitude tip works even with sticks idle (lift nose / tail / side).
    tip = self._attitude_tip(pitch_signed, roll_delta)
    if tip.side != CollisionSide.NONE and not moving_cmd:
      self._bout_cmd = 0
      self._bout_kind = ""
      self._impact_side = CollisionSide.NONE
      self._impact_since_ms = None
      return tip
    if not moving_cmd:
      self._bout_cmd = 0
      self._bout_kind = ""
      self._bout_delta_v = 0.0
      self._impact_side = CollisionSide.NONE
      self._impact_since_ms = None
      return StuckReport.clear()

    kind, cmd_value = self._primary_cmd(cmd_forward, cmd_spin, cmd_strafe, cmd_deadband)
    if self._bout_cmd == 0 or kind != self._bout_kind or (cmd_value >= 0) != (self._bout_cmd >= 0):
      self._bout_cmd = cmd_value
      self._bout_kind = kind
      self._bout_started_ms = newest.timestamp_ms
      self._bout_last_ms = newest.timestamp_ms
      self._bout_max_abs_accel = abs_a if kind == "fwd" else abs_lat
      self._bout_max_horizontal = horiz if newest.accel_valid else 0.0
      self._bout_delta_v = 0.0
      self._bout_enc_start = newest.encoder_sum
    else:
      dt_s = max(0.0, (newest.timestamp_ms - self._bout_last_ms) / 1000.0)
      self._bout_last_ms = newest.timestamp_ms
      if newest.accel_valid:
        if kind == "fwd":
          self._bout_delta_v += a_long * dt_s
          if abs_a > self._bout_max_abs_accel:
            self._bout_max_abs_accel = abs_a
        elif kind == "strafe":
          self._bout_delta_v += a_lat * dt_s
          if abs_lat > self._bout_max_abs_accel:
            self._bout_max_abs_accel = abs_lat
        if horiz > self._bout_max_horizontal:
          self._bout_max_horizontal = horiz

    impact_hit, impact_detail, impact_mag = self._opposing_impact(
      newest.accel_valid,
      cmd_forward,
      cmd_strafe,
      cmd_deadband,
      a_long,
      a_lat,
    )
    if impact_hit == CollisionSide.NONE:
      self._impact_side = CollisionSide.NONE
      self._impact_since_ms = None
    elif impact_hit != self._impact_side:
      self._impact_side = impact_hit
      self._impact_since_ms = newest.timestamp_ms

    oldest = self._samples[0]
    dt_ms = max(1, newest.timestamp_ms - oldest.timestamp_ms)
    if dt_ms < self._settings.stuck_window_ms // 2 and tip.side == CollisionSide.NONE:
      # Still allow instant crash before the window is warm.
      if (
        impact_hit != CollisionSide.NONE
        and impact_mag >= self._settings.accel_crash_mps2
      ):
        return StuckReport(
          level=StuckLevel.STUCK,
          side=impact_hit,
          detail=f"crash {impact_detail}",
          cause=StuckCause.CRASH,
        )
      return StuckReport.clear()

    enc_delta = abs(newest.encoder_sum - oldest.encoder_sum)
    wheels_moving = enc_delta >= self._settings.encoder_tick_threshold

    side = CollisionSide.NONE
    detail = ""
    cause = StuckCause.NONE
    bout_ms = newest.timestamp_ms - self._bout_started_ms
    bout_enc = abs(newest.encoder_sum - self._bout_enc_start)

    if tip.side != CollisionSide.NONE:
      return tip
    if impact_hit != CollisionSide.NONE and impact_mag >= self._settings.accel_crash_mps2:
      side = impact_hit
      detail = f"crash {impact_detail}"
      cause = StuckCause.CRASH
    elif (
      self._settings.soft_impact_enabled
      and impact_hit != CollisionSide.NONE
      and self._impact_since_ms is not None
      and newest.timestamp_ms - self._impact_since_ms
      >= self._settings.impact_hold_ms
    ):
      side = impact_hit
      detail = impact_detail
      cause = StuckCause.SOFT_IMPACT

    if (
      side == CollisionSide.NONE
      and self._settings.slip_enabled
      and newest.accel_valid
      and kind in ("fwd", "strafe")
      and bout_ms >= self._settings.stuck_window_ms
      and bout_enc >= self._settings.encoder_tick_threshold
      and self._bout_max_abs_accel < self._settings.accel_launch_mps2
      and self._bout_max_horizontal < self._settings.accel_launch_mps2
      and abs(self._bout_delta_v) < self._settings.slip_delta_v_mps
    ):
      if kind == "fwd":
        side = CollisionSide.FRONT if cmd_forward < 0 else CollisionSide.REAR
      else:
        side = CollisionSide.RIGHT if cmd_strafe > 0 else CollisionSide.LEFT
      detail = (
        f"slip enc={bout_enc}"
        f" max_a={self._bout_max_abs_accel:.2f}"
        f" horiz={self._bout_max_horizontal:.2f}"
        f" dv={self._bout_delta_v:+.2f}"
      )
      cause = StuckCause.SLIP

    if side == CollisionSide.NONE and abs(cmd_spin) > cmd_deadband:
      yaw_delta = self._yaw_delta_deg(oldest.yaw_deg, newest.yaw_deg)
      expected = self._frame.yaw_spin_sign * (1.0 if cmd_spin > 0 else -1.0)
      if abs(yaw_delta) < self._settings.yaw_error_deg * 0.25 and wheels_moving:
        side = CollisionSide.UNKNOWN
        detail = f"yaw stall ({yaw_delta:.1f} deg)"
        cause = StuckCause.YAW
      elif yaw_delta * expected < 0 and abs(yaw_delta) >= self._settings.yaw_error_deg * 0.5:
        side = CollisionSide.LEFT if cmd_spin > 0 else CollisionSide.RIGHT
        detail = f"yaw wrong-way {yaw_delta:.1f}"
        cause = StuckCause.YAW

    if side == CollisionSide.NONE:
      return StuckReport.clear()

    return StuckReport(
      level=StuckLevel.STUCK, side=side, detail=detail or "stuck", cause=cause,
    )

  def _attitude_tip(self, pitch_signed: float, roll_delta: float) -> StuckReport:
    """Tip vs rest pose — no stick / encoder requirement."""
    if abs(pitch_signed) >= self._settings.pitch_lift_deg:
      side = CollisionSide.FRONT if pitch_signed > 0 else CollisionSide.REAR
      return StuckReport(
        level=StuckLevel.STUCK,
        side=side,
        detail=f"pitch {pitch_signed:.1f}",
        cause=StuckCause.ATTITUDE_TIP,
      )
    if abs(roll_delta) >= self._settings.roll_bump_deg:
      side = CollisionSide.RIGHT if roll_delta > 0 else CollisionSide.LEFT
      return StuckReport(
        level=StuckLevel.STUCK,
        side=side,
        detail=f"roll {roll_delta:.1f}",
        cause=StuckCause.ATTITUDE_TIP,
      )
    return StuckReport.clear()

  def _opposing_impact(
    self,
    accel_valid: bool,
    cmd_forward: int,
    cmd_strafe: int,
    cmd_deadband: int,
    a_long: float,
    a_lat: float,
  ) -> tuple[CollisionSide, str, float]:
    """Return (side, detail, |opposing a|) when accel fights the command."""
    if not accel_valid:
      return CollisionSide.NONE, "", 0.0
    # Soft threshold used for magnitude; crash path compares to accel_crash_mps2.
    soft = self._settings.accel_impact_mps2
    if abs(cmd_forward) > cmd_deadband:
      if cmd_forward < 0 and a_long <= -soft:
        return CollisionSide.FRONT, f"a={a_long:+.2f}", abs(a_long)
      if cmd_forward > 0 and a_long >= soft:
        return CollisionSide.REAR, f"a={a_long:+.2f}", abs(a_long)
    if abs(cmd_strafe) > cmd_deadband:
      if cmd_strafe > 0 and a_lat <= -soft:
        return CollisionSide.RIGHT, f"lat={a_lat:+.2f}", abs(a_lat)
      if cmd_strafe < 0 and a_lat >= soft:
        return CollisionSide.LEFT, f"lat={a_lat:+.2f}", abs(a_lat)
    return CollisionSide.NONE, "", 0.0

  @staticmethod
  def _primary_cmd(
    cmd_forward: int,
    cmd_spin: int,
    cmd_strafe: int,
    cmd_deadband: int,
  ) -> tuple[str, int]:
    if abs(cmd_forward) > cmd_deadband:
      return "fwd", cmd_forward
    if abs(cmd_strafe) > cmd_deadband:
      return "strafe", cmd_strafe
    if abs(cmd_spin) > cmd_deadband:
      return "spin", cmd_spin
    return "", 0

  @staticmethod
  def _yaw_delta_deg(start_deg: float, now_deg: float) -> float:
    return (now_deg - start_deg + 180.0) % 360.0 - 180.0
