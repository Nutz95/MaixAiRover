# Obstacle awareness (IMU calib + stuck HUD)

After the pad connects and the peripheral checklist is dismissed (**touch OK** or **Xbox A**), an optional **IMU calibration** wizard runs: rest → creep forward/reverse → spin CW/CCW. Confirm steps with **A** / OK, or **Skip** to keep default signs.

## What it learns

- Rest `pitch0` / `roll0`
- Pitch / yaw / forward-accel signs
- Forward accel axis from the creep transient

When the script reaches **DONE**, stuck detection is armed immediately.

## Stuck overlay

Informational only (no auto unstick yet). Card shows estimated contact side.

Detection rules:

- **Attitude tip** — pitch/roll vs rest calib (works even with sticks idle: lift nose/tail/side)
- **Crash** — short opposing accel ≥ `accel_crash_mps2` (violent hit, instant)
- **Soft impact** — off by default (`soft_impact_enabled`); was causing cruise false positives
- **Slip** — off by default
- **Yaw stall** — spin commanded but attitude yaw barely moves

We only watch the **sum** of encoder ticks (motion yes/no), not per-wheel mismatch. Yahboom `set_car_motion` already runs closed-loop PID per motor.

## Probe log (TCP)

`nc` = **netcat** (Unix). On Windows PowerShell it is usually missing. Use:

```powershell
python tools/obstacle_probe_listen.py 192.168.1.100
```

(Replace with the MaixCAM IP. Port default 9400.)

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

## Next: heading hold (planned)

Straight drive currently drifts (mecanum slip). Planned fix — **not built yet**:

1. On forward/back with spin stick near zero, latch yaw at bout start
2. P (then PI) on yaw error → add a small `axis_spin` correction
3. Disable while user commands spin / strafe
4. Tunables in `config.json` (`heading_hold_gain`, deadband)

Needs the same TCP probe for yaw error while tuning.
