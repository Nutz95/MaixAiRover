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

Strafe comes from `trigger_diff` = RT − LT (both pressed → cancel). Config: `mapping.axes.drive_strafe`.

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
