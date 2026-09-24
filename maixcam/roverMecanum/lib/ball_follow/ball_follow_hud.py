"""Ball-follow mode LED, bbox, and trajectory HUD."""

from maix import image

from lib.ball_follow.ball_follow_snapshot import BallFollowSnapshot

# Below the top-left exit pad (8,8,44×44) so the LED never covers the hit target.
_LED_X = 30
_LED_Y = 74
_LED_R = 14


class BallFollowHud:
  """Draw ball-follow status and observation overlays on the camera frame."""

  def __init__(self, width: int, height: int):
    """Remember display size for layout (currently unused; reserved for scale)."""
    self.width = width
    self.height = height

  def draw(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    """Draw mode LED, blob box, and trajectory (no hard-to-read text badge)."""
    self._draw_mode_led(img, ball_snapshot)
    if not ball_snapshot.enabled:
      return
    self._draw_trajectory(img, ball_snapshot)
    observation = ball_snapshot.observation
    box_color = (
      image.Color.from_rgb(240, 80, 80)
      if ball_snapshot.color == "red"
      else image.Color.from_rgb(80, 220, 80)
    )
    if observation is None:
      return
    scale_x = img.width() / max(1, observation.image_width)
    scale_y = img.height() / max(1, observation.image_height)
    left = int((observation.center_x - observation.width // 2) * scale_x)
    top = int((observation.center_y - observation.height // 2) * scale_y)
    width = max(1, int(observation.width * scale_x))
    height = max(1, int(observation.height * scale_y))
    img.draw_rect(left, top, width, height, box_color, thickness=3)
    img.draw_circle(
      int(observation.center_x * scale_x),
      int(observation.center_y * scale_y),
      4,
      image.Color.from_rgb(255, 255, 255),
      thickness=-1,
    )

  def _draw_mode_led(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    """Colour LED: grey=manual, green/red=follow that colour."""
    if not ball_snapshot.enabled:
      fill = image.Color.from_rgb(70, 70, 70)
    elif ball_snapshot.color == "red":
      fill = image.Color.from_rgb(230, 40, 40)
    else:
      fill = image.Color.from_rgb(40, 220, 70)
    img.draw_circle(_LED_X, _LED_Y, _LED_R, fill, thickness=-1)
    img.draw_circle(_LED_X, _LED_Y, _LED_R, image.COLOR_WHITE, thickness=2)
    if ball_snapshot.enabled:
      # Bright core — reads as an “on” LED even on turbo depth.
      img.draw_circle(
        _LED_X - 3, _LED_Y - 3, 4,
        image.Color.from_rgb(255, 255, 255), thickness=-1,
      )

  def _draw_trajectory(self, img, ball_snapshot: BallFollowSnapshot) -> None:
    previous_x = None
    previous_y = None
    for point in ball_snapshot.trajectory:
      scale_x = img.width() / max(1, point.image_width)
      scale_y = img.height() / max(1, point.image_height)
      point_x = int(point.center_x * scale_x)
      point_y = int(point.center_y * scale_y)
      if previous_x is not None and previous_y is not None:
        img.draw_line(
          previous_x, previous_y, point_x, point_y,
          image.Color.from_rgb(255, 180, 40), thickness=2,
        )
      img.draw_circle(
        point_x, point_y, 3, image.Color.from_rgb(255, 180, 40), thickness=-1,
      )
      previous_x = point_x
      previous_y = point_y
