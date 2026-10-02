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
| A | Stop (**or Confirm** when checklist / IMU calib modal is open) |
| **View / Select** | Toggle **ball-follow** mode |
| **Menu / Start** | Cycle ball color (green ↔ red) |

Strafe comes from `trigger_diff` = RT − LT (both pressed → cancel). Config: `mapping.axes.drive_strafe`.

## Post-connect modals

1. **Peripherals checklist** — dismiss with touch **OK** or **A**.
2. **IMU calibration** (if `obstacle_nav.calib_after_connect`) — scripted creep/spin; **A**/OK confirms intro & done; **Skip** keeps defaults. See [obstacle_nav.md](obstacle_nav.md).

After that, stuck/collision awareness runs in all modes and may show a top-down contact overlay.

## Ball-follow

When enabled (View), sticks are overridden: vision drives `forward` + `spin` only via the active backend (`set_car_motion` on Yahboom). Stick/trigger gauges hide while following; a colour LED (grey=manual, green/red=follow) shows the active mode.

**Follow = hold a formation.** Spin from image **X error only** (no blob-velocity feedforward while tracking — ego yaw poisons that signal). Servo forward/back on image **Y** (mid-frame setpoint). Image velocity is sampled only while spin≈0 and used to pick search direction when the ball exits the frame.

Align yaw ceiling uses `t = (|x−0.5| / align_spin_full_error) ^ align_spin_curve`. **`curve < 1`** (default `0.55`) is firm just outside `horizontal_deadzone`; `curve > 1` softens the center (lags on center passes). Blob height also scales urgency. See `docs/align_spin_curve.md`.

Approach soft-cap / search yaw clamps live under `config.json` → `ball_follow`.

LAB blob colours live only under `ball_follow.colors` in `config.json` (and `color_order` for Start cycling). Encoder closed-loop allows low `min_*_axis` trim (no Keyestudio-style high breakaway).

Optional `ball_follow.depth_fusion_enabled`: DepthAnything runs **async** (one frame in flight; HUD stays fluid). Ball detect/track/drive are independent — depth busy only freezes the last distance band. `depth_view`: `blend` / `depth` / `rgb`. `depth_interval_ms` can be low (e.g. 50) in `depth` mode. `depth_contour_thickness` dilates Canny edges (1–4). Display only — approach distance still uses blob size, not depth.

## Mecanum body velocities (Yahboom `set_car_motion`)

| Axis | Meaning | How you get it |
|------|---------|----------------|
| **vx** | Forward / reverse | Left stick Y |
| **vy** | **Crab** (strafe sideways) | **LT / RT** (`trigger_diff`) |
| **vz** | Spin in place (yaw) | Right stick X (+ left X as pivot blend) |

- **Diagonal**: D-pad corners (`diag_fl` …) → `vx` + `vy` together. Same if you hold forward stick + a trigger.
- **Drift-like**: hold Left Y (vx) + Right X (vz) — the STM32 mixes mecanum; no separate “drift mode” API.
- **Speed %**: `yahboom.max_vx/vy/vz` are the physical ceilings (m/s, rad/s). LB/RB change `session_max_speed` 0…255, which scales all three: `v = axis × max_v × (speed/255)`.

Maix `config.json` already mirrors Keyestudio: triggers=crab, D-pad diagonals, right stick=spin, left X=pivot.

With `drive_backend=yahboom`, Maix does **not** run `MecanumMixer`. Flow:

1. Stick mapping → `DriveCommand` (forward / strafe / spin)
2. `DriveCommandChassisMapper` → body velocity `vx, vy, vz` (m/s, rad/s)
3. USB `set_car_motion` → **STM32** mixes mecanum + **closed-loop PID on encoders**

So yes: motion uses encoders. Open-loop `set_motor` PWM is only for the USB bench tool.

Yahboom frame: `+vx` forward, `+vy` left, `+vz` CCW — mapper negates forward, strafe and spin. Requires motor wiring M1=FL, M2=RL, M3=FR, M4=RR (see `docs/yahboom.md`).

## HUD (connected)

Once Xbox is paired/connected, the camera overlay shows:

- Left / right stick gauges
- LT / RT bars
- D-pad dots
- A / B / X / Y cluster (lit when pressed)
- Speed bar with LB / RB highlight
- Dual battery bars (CAM % / ROV %)
- DISC to disconnect (hidden while ball-follow is on — use View/Select to leave follow first)
- DBG panel (also hidden in ball-follow)

Disconnected: PAIR + CONNECT only (no on-screen motor pad).
