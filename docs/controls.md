# Xbox controls

Default mapping matches the previous Keyestudio mecanum rover (revision 4).

![Xbox controller mapping](../resources/maixcam2/XBoxControler.jpg)

| Input | Action |
|-------|--------|
| Left stick Y | Forward / reverse |
| **LT** | **Crab left** (strafe) |
| **RT** | **Crab right** (strafe) |
| Right stick X | Spin in place |
| Left stick X | Pivot / yaw blend |
| D-pad | Full-axis presets (incl. diagonals) |
| LB / RB | Decrease / increase session max speed |
| A | Stop |
| **View / Select** | Toggle **ball-follow** mode |
| **Menu / Start** | Cycle ball color (green ↔ red) |

Strafe comes from `trigger_diff` = RT − LT (both pressed → cancel). Config: `mapping.axes.drive_strafe`.

## Ball-follow

When enabled (View), sticks are overridden: vision drives `forward` + `spin` only via the active backend (`set_car_motion` on Yahboom). Stick/trigger gauges hide while following; a colour LED (grey=manual, green/red=follow) shows the active mode. Lost ball: wait → encoder ~360° spin → IMU compass fix → pause → retreat → repeat.

LAB blob colours live only under `ball_follow.colors` in `config.json` (and `color_order` for Start cycling). Encoder closed-loop allows low `min_*_axis` trim (no Keyestudio-style high breakaway).

Optional `ball_follow.depth_fusion_enabled`: DepthAnything runs **async** (one frame in flight; HUD stays fluid). Ball detect/track/drive are independent — depth busy only freezes the last distance band. `depth_view`: `blend` / `depth` / `rgb`. `depth_interval_ms` can be low (e.g. 50) in `depth` mode. `depth_contour_thickness` dilates Canny edges (1–4). Display only — approach distance still uses blob size, not depth.

## Yahboom path (no Maix wheel mixer)

With `drive_backend=yahboom`, Maix does **not** run `MecanumMixer`. Flow:

1. Stick mapping → `DriveCommand` (forward / strafe / spin)
2. `DriveCommandChassisMapper` → body velocity `vx, vy, vz` (m/s, rad/s)
3. USB `set_car_motion` → **STM32** mixes mecanum + **closed-loop PID on encoders**

So yes: motion uses encoders. Open-loop `set_motor` PWM is only for the USB bench tool.

Yahboom frame: `+vx` forward, `+vy` left, `+vz` CCW — the mapper flips strafe/spin signs so RT still means “right”.

## HUD (connected)

Once Xbox is paired/connected, the camera overlay shows:

- Left / right stick gauges
- LT / RT bars
- D-pad dots
- A / B / X / Y cluster (lit when pressed)
- Speed bar with LB / RB highlight
- Dual battery bars (CAM % / ROV %)
- DISC to disconnect

Disconnected: PAIR + CONNECT only (no on-screen motor pad).
