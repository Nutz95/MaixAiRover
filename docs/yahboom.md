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

**Frame (Rosmaster):** `+vx` forward, `+vy` **left**, `+vz` CCW. Teleop “strafe right / spin CW” are negated in `DriveCommandChassisMapper` before USB.

**Xbox strafe:** LT = crab left, RT = crab right (`mapping.axes.drive_strafe = trigger_diff`).

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

Encoder motor pinout / 56:1 / 178 rpm: [`resources/Motors/README.md`](../resources/Motors/README.md).

## Config

```json
"drive_backend": "yahboom",
"yahboom": { "port": "ch340", "baud": 115200, "max_vx": 1.0, "max_vy": 1.0, "max_vz": 5.0 },
"rover": { "deadzone_percent": 0 }
```

On MaixCAM2, `port: "ch340"` (or `""` / `"auto"`) uses **libusb** to the QinHeng CH340  
(`1a86:7523`). Stock Maix kernel has no `CONFIG_USB_SERIAL`, so there is no `/dev/ttyUSB0`.

Plug Yahboom **Micro-USB « Connect USB »** into a Maix **USB host** port. DC 6–13 V must be ON.

`"drive_backend": "esp"` keeps the Waveshare dual-UART path.

Deploy (overwrite remote config):

```powershell
.\tools\deploy_rover_mecanum.ps1 -MaixCamIp 192.168.1.100 -DeployOnly -SyncConfig
```

## Host USB bench (PC)

With Micro-USB data on the PC (e.g. `COM15`) and DC power on:

```powershell
.\tools\yahboom_bench.ps1 -Port COM15
```

Menu: ping / battery / IMU 9-axis / encoders / per-motor PWM fwd-rev-stop.  
Needs `pyserial` + `Rosmaster_Lib` (script installs them on first run).
