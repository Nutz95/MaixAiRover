# Xbox controls

Default mapping matches the previous Keyestudio mecanum rover (revision 4).

![Xbox controller mapping](../resources/maixcam2/XBoxControler.jpg)

| Input | Action |
|-------|--------|
| Left stick Y | Forward / reverse |
| LT / RT | Strafe (RT − LT) |
| Right stick X | Spin in place |
| Left stick X | Pivot (brake one side) |
| D-pad | Full-axis presets (incl. diagonals) |
| LB / RB | Decrease / increase session max speed |
| A | Stop |

Config: `maixcam/roverMecanum/config.json` → `mapping`.

## HUD (connected)

Once Xbox is paired/connected, the camera overlay shows:

- Left / right stick gauges
- LT / RT bars
- D-pad dots
- A / B / X / Y cluster (lit when pressed)
- Speed bar with LB / RB highlight
- DISC to disconnect

Disconnected: PAIR + CONNECT only (no on-screen motor pad).

For Xbox-only tests without a motor board, keep `i2c.mode` = `stub` in `config.json`.
