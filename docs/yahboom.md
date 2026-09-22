# Yahboom ROS Robot Expansion Board

Product: [Yahboom ROS Driver Board](https://category.yahboom.net/products/ros-driver-board) (STM32F103).  
Docs: [yahboom.net/study/ROS-Driver-Board](https://www.yahboom.net/study/ROS-Driver-Board) · local photos in `resources/yahboom/`.

## Firmware

- Ships **pre-flashed** with Rosmaster firmware — talk over USB serial with binary commands.
- Reflash only if needed: vendor `.hex` + **MCUISP** (BOOT0 + RESET). **Not PlatformIO.**
- Annex / hex / `py_install`: see `I:\GIT\ROS-robot-expansion-board\Annex_Download_Link.txt`.

## How motors are driven (important)

| API | Encoders / PID | Use |
|-----|----------------|-----|
| **`set_car_motion(vx,vy,vz)`** | **Yes** — STM32 mixes mecanum + closed-loop PID on encoders | **Teleop / tracking (our path)** |
| `set_motor(m1..m4)` | **No** — open-loop PWM `[-100,100]` | Bench / ignore for navigation |
| `set_car_run(...)` | Discrete presets | Not used |

Maix still does stick mapping; it sends **body velocity**, not wheel PWM. The board counters deadband, motor mismatch, and slip via encoders. Set `rover.deadzone_percent` to **0** for object-follow (stick deadzone is the wrong place to fight mechanical deadband).

## USB wiring (MaixCAM2)

| Port on board | Role |
|---------------|------|
| **Micro-USB « Connect USB »** | CH340 data (VID `1a86:7523`) @ **115200** |
| **Type-C** | **5 V OUT only** — not the control link |
| DC 6–13 V IN | Board + motor supply |

## Motor map (this rover)

| Wheel | Yahboom channel |
|-------|-----------------|
| Front right | Motor 1 |
| Front left | Motor 2 |
| Rear right | Motor 3 |
| Rear left | Motor 4 |

## Config

```json
"drive_backend": "yahboom",
"yahboom": { "port": "COM12", "baud": 115200, "max_vx": 1.0, "max_vy": 1.0, "max_vz": 5.0 },
"rover": { "deadzone_percent": 0 }
```

`"drive_backend": "esp"` keeps the Waveshare dual-UART path.
