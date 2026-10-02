"""DriveMode SELECT cycle."""

from lib.app.drive_mode import DriveMode


def test_cycle_order() -> None:
  assert DriveMode.MANUAL.next_mode() is DriveMode.AVOID
  assert DriveMode.AVOID.next_mode() is DriveMode.FOLLOW
  assert DriveMode.FOLLOW.next_mode() is DriveMode.MANUAL


def test_flags() -> None:
  assert not DriveMode.MANUAL.uses_depth()
  assert not DriveMode.MANUAL.uses_avoidance()
  assert not DriveMode.MANUAL.uses_ball_follow()
  assert DriveMode.AVOID.uses_depth()
  assert DriveMode.AVOID.uses_avoidance()
  assert not DriveMode.AVOID.uses_ball_follow()
  assert DriveMode.FOLLOW.uses_depth()
  assert DriveMode.FOLLOW.uses_avoidance()
  assert DriveMode.FOLLOW.uses_ball_follow()
