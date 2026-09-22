# ESP rover coordinator (Waveshare)

Hardware brain: [Waveshare General Driver for Robots](https://www.waveshare.com/wiki/General_Driver_for_Robots)
drives a **local left/right** pair via onboard TB6612 + encoders (PID @ 100 Hz).
Two boards (front + rear) run the **same** firmware; OTA hostname differs.

```
MaixCAM2 --UART4--> front Waveshare IO4/IO5 --TB6612--> FL/FR
MaixCAM2 --UART2--> rear  Waveshare IO4/IO5 --TB6612--> RL/RR
```

## Firmware layout (`src/`)


| Module                                           | Responsibility                           |
| ------------------------------------------------ | ---------------------------------------- |
| `main.cpp`                                       | Wire objects; spawn cmd + wifi tasks     |
| `settings.h`                                     | Pins, encoder model, PID, task sizes     |
| `front_drive_board.*`                            | Local pair setpoints, PID loop, encoders |
| `tb6612_channel.*`                               | One H-bridge PWM channel                 |
| `quadrature_encoder.*`                           | Full-quadrature ISR counters             |
| `wheel_velocity_pid.*`                           | RPM-space PID                            |
| `command_dispatcher.*`                           | Line protocol → drive / wifi / BAT       |
| `binary_protocol.h` / `binary_command_handler.*` | Compact `0xA5` frames + TELEM            |
| `board_sensors.*`                                | INA219 + QMI8658 + AK09918               |
| `drive_failsafe.*`                               | Stop if no SPEED/PWM for 1.5 s           |
| `serial_line_reader.*`                           | LF text + binary framing on UART0        |
| `wifi_runtime.*` / `wifi_console.*`              | STA, OTA, TCP :2333                      |
| `protocol_reply.*`                               | `OK`/`ERR` → Serial + WiFi               |
| `coordinator_lock.*` / `coordinator_guard.*`     | Mutex                                    |




## Wiring

See [docs/wiring.md](../../docs/wiring.md). Board supply **7–13 V** required for motors.

## Flash

IPs: `[devices.json](devices.json)`. Envs: `waveshare_front` / `waveshare_rear` (+ `_ota`).

```powershell
.\tools\flash_esp_coordinator.ps1 -Board rear -Port COM11 -Monitor
.\tools\flash_esp_coordinator.ps1 -Board front -Ota
.\tools\flash_esp_coordinator.ps1 -Board both -Ota
python tools\drive_esp_coordinator.py --port COM11
# SPEED 25 25 0 0
```

WiFi OTA: `SOARM_WIFI_SSID` / `SOARM_WIFI_PASS`.