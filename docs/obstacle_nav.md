# Obstacle awareness (IMU + vision strategy)

After the pad connects and the peripheral checklist is dismissed (**touch OK** or **Xbox A**), an optional **IMU calibration** wizard runs: rest → creep forward/reverse → spin CW/CCW. Confirm with **A** / OK, or **Skip** for defaults.

## What calib learns

- Rest `pitch0` / `roll0`
- Pitch / yaw / forward-accel signs
- Forward accel axis from the creep transient

When the script reaches **DONE**, stuck detection is armed immediately.

**Planned next wizard step (after IMU):** depth ground split — sample the lower strip while still, propose the green-floor / obstacle boundary, confirm with **A** / Skip. Does not replace IMU; only tunes `ground_top_ratio` (and related) for the tilted cam.

When `depth_ground_calib` is true, after IMU **DONE** / **Skip** (or when IMU calib is off), the live camera opens with a ground-split prompt. **A** applies the proposed `ground_top_ratio` for the session; **Skip** keeps config.

## Stuck overlay (failsafe)

Informational only for now (no auto unstick maneuvers yet). Card shows estimated contact side.

Detection rules:

- **Attitude tip** — pitch/roll vs rest (works with sticks idle)
- **Crash** — short opposing accel ≥ `accel_crash_mps2` (instant)
- **Soft impact** / **slip** — off by default (mecanum vibe false-triggers)

Probe TCP (Windows): `python tools/obstacle_probe_listen.py <maix-ip>`

## Strategy without ToF / LiDAR

Camera is **tilted down** (ball on floor). Lower image = ground + ball; mid = near obstacles ahead.

**Drive modes (SELECT):** MANUAL (no depth/avoid) → AVOID (depth + soft dodge, yellow LED) → FOLLOW (ball + avoid). Default MANUAL keeps teleop fluid. See [architecture.md](architecture.md).

HUD (`show_roi_guides` + depth):

- **Green** horizontal = calibrated ground split (below = floor, ignored for avoid)
- **Red/orange L / C / R blocks** above that line = last depth hit (AVOID/FOLLOW only)
- **Dodge vector** when avoidance is armed
- Ball detect only in FOLLOW
- Connected HUD: no DISC/DBG buttons — **Xbox X** opens debug, **B** returns to teleop

**Depth = colors, not meters.** Red/orange in the **obstacle** band (above the green floor split) = dodge. Yellow = caution. Floor strip below the split is ignored for avoidance (ball lives there — mask the ball bbox). Sampler uses **top-3 mean** warmth per column across ``obstacle_band_count`` (default 5) so corridors (hot sides, cool center) stay distinct.

Collision IMU is **on** (`stuck_detection_enabled`). **Attitude tip** (lift nose/tail/side) **cuts drive** (motors stop). Crash / other causes still show the HUD card only until tuned.

| Layer | Source | Use |
| --- | ---: | --- |
| Primary obstacles | DepthAnything turbo warmth peaks in obstacle L/C/R | avoid; not used for ball distance |
| Ground strip | Lower FOV + green split | calib vertical limits only |
| Secondary | Sparse LK + gyro derotation | ground crop slip; obstacle crop TTC / L-R balance |
| Failsafe | This IMU stuck HUD | tip / crash when vision misses |

Avoidance v0: **strafe to freer side first**; HUD arrow in AVOID; same override in FOLLOW. Orbit only if both sides blocked or ball would leave FOV. See [plan.md](plan.md).

Soft override is live when `avoidance_enabled` **and** mode is AVOID or FOLLOW.

## Config (`obstacle_nav`)

| Key | Default | Role |
| --- | ---: | --- |
| `stuck_window_ms` | 350 | Bout / analysis window |
| `pitch_lift_deg` / `roll_bump_deg` | 15 / 12 | Attitude tip vs rest |
| `accel_crash_mps2` | 5.0 | Instant violent opposing hit |
| `accel_impact_mps2` | 3.0 | Soft-impact floor (if enabled) |
| `soft_impact_enabled` | false | Held soft impacts (noisy) |
| `impact_hold_ms` | 150 | Soft-impact hold time |
| `slip_enabled` | false | Slip off — vibe false-triggers |
| `probe_tcp_port` | 9400 | TCP text probe (`0` = off) |
| `stuck_detection_enabled` | true | IMU stuck HUD; tip cuts drive |
| `show_roi_guides` | true | Thin ground / obstacle HUD lines |
| `ground_top_ratio` | 0.50 | Y split at mid-frame: below = ground |
| `obstacle_top_ratio` | 0.18 | Top of obstacle band |
| `obstacle_left_ratio` / `obstacle_right_ratio` | 0.08 / 0.92 | Obstacle corridor (mid width) |
| `obstacle_band_count` | 5 | Vertical columns (3–9); finer grid = smaller HUD zones |
| `depth_ground_calib` | true | After IMU: propose ground_top from **light-green** depth; stick Y nudges; A confirms |
| `ground_floor_warmth` | 0.08 | Reject rows warmer than ~orange while seeking green |
| `avoidance_enabled` | true | Soft L/C/R drive override + HUD arrow (AVOID/FOLLOW) |
| `avoidance_close_warmth` | 0.22 | Hot = dodge (top-k warmth) |
| `avoidance_caution_warmth` | 0.10 | Soft stop-forward / bias |
| `avoidance_strafe_axis` / `avoidance_reverse_axis` | 12000 / 8000 | Override magnitudes |

## Next: heading hold (planned)

Straight drive drifts (mecanum slip). Planned:

1. Latch yaw when forward/back with spin stick near zero
2. P (then PI) on yaw error → small `axis_spin` correction
3. Disable while user commands spin / strafe
4. Tunables in `config.json` (`heading_hold_gain`, deadband)
