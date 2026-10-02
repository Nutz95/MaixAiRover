# Obstacle awareness (IMU + vision strategy)

After the pad connects and the peripheral checklist is dismissed (**touch OK** or **Xbox A**), an optional **IMU calibration** wizard runs: rest → creep forward/reverse → spin CW/CCW. Confirm with **A** / OK, or **Skip** for defaults.

## What calib learns

- Rest `pitch0` / `roll0`
- Pitch / yaw / forward-accel signs
- Forward accel axis from the creep transient

When the script reaches **DONE**, stuck detection is armed immediately.

## Stuck overlay (failsafe)

Informational only for now (no auto unstick maneuvers yet). Card shows estimated contact side.

Detection rules:

- **Attitude tip** — pitch/roll vs rest (works with sticks idle)
- **Crash** — short opposing accel ≥ `accel_crash_mps2` (instant)
- **Soft impact** / **slip** — off by default (mecanum vibe false-triggers)

Probe TCP (Windows): `python tools/obstacle_probe_listen.py <maix-ip>`

## Strategy without ToF / LiDAR

Camera is **tilted down** (ball on floor). Lower image = ground + ball; mid = near obstacles ahead.

HUD **ROI guides** (`show_roi_guides`):

- **Green** horizontal = ground split — align the real floor here
- **Blue wash + rails + mid line** = obstacle band (left / center / right halves) — this is where depth/OF will look

Collision IMU is **on** (`stuck_detection_enabled`). **Attitude tip** (lift nose/tail/side) **cuts drive** (motors stop). Crash / other causes still show the HUD card only until tuned.

| Layer | Source | Use |
| --- | --- | --- |
| Primary obstacles | DepthAnything async, low-res, obstacle ROI crop | near/mid/far bands → avoidance |
| Secondary | Sparse LK + gyro derotation | ground crop slip; obstacle crop TTC / L-R balance |
| Failsafe | This IMU stuck HUD | tip / crash when vision misses |

Optical flow is **not** the main obstacle sensor. Depth bands drive avoidance v0; OF improves ego-motion / timing cues. Full planner (occupancy + DWA) comes after bands work. See [plan.md](plan.md) and [roadmap.md](roadmap.md).

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
| `obstacle_left_ratio` / `obstacle_right_ratio` | 0.15 / 0.85 | Obstacle corridor sides |

## Next: heading hold (planned)

Straight drive drifts (mecanum slip). Planned:

1. Latch yaw when forward/back with spin stick near zero
2. P (then PI) on yaw error → small `axis_spin` correction
3. Disable while user commands spin / strafe
4. Tunables in `config.json` (`heading_hold_gain`, deadband)
