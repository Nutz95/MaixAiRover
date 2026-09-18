# ESP rover coordinator (Waveshare)

Hardware brain of the rover: [Waveshare General Driver for Robots](https://www.waveshare.com/wiki/General_Driver_for_Robots)
(ESP32) talks to the Hiwonder motor board over I2C and accepts drive commands
from MaixCAM2 (or a PC) over UART.

```
MaixCAM2  --UART 115200-->  ESP32 coordinator  --I2C 0x34-->  Hiwonder motors
```

## Wiring

| Waveshare IIC | Hiwonder |
|---------------|----------|
| SDA (GPIO32) | SDA |
| SCL (GPIO33) | SCL |
| GND | GND |

Power Hiwonder **VM** separately (5–15 V). MaixCAM UART TX/RX → ESP UART
(pins TBD in `docs/wiring.md` — use USB serial for PC smoke tests).

## Flash

WiFi for OTA uses system env vars (same workstation as SOARM / AutoBalancing):

- `SOARM_WIFI_SSID`
- `SOARM_WIFI_PASS`

```powershell
# First flash over USB (hold Download + Reset if needed)
.\tools\flash_esp_coordinator.ps1 -Port COM9

# Later: OTA (optional; only if WiFi joined - get IP from Serial or WIFI cmd)
.\tools\flash_esp_coordinator.ps1 -Ota -OtaHost 192.168.20.148
```

## Serial protocol (115200)

| Cmd | Reply |
|-----|--------|
| `PING` | `OK PONG` |
| `INIT [type] [pol]` | motor type (default 3=JGB) |
| `STOP` / `SPEED m1 m2 m3 m4` / `PWM …` | drive |
| `BAT` / `ENC` | telemetry |
| `WIFI` | `OK WIFI <ip>` or error |

Failsafe: no `SPEED`/`PWM` for 1.5 s → stop.

PC smoke: `python tools/drive_esp_coordinator.py --port COM9 --demo`

WiFi console (after `wifi: OK ip=...`):

```powershell
python tools\wifi_console_client.py --host 192.168.20.148
python tools\wifi_console_client.py --host 192.168.20.148 -c SCAN -c PING
```

Port **2333**. Same commands as USB Serial (`PING`, `SCAN`, `SPEED`, …).

## Later (not in this firmware yet)

- STS3215 bus servos (gimbal + ToF mount)
- WS2812 corner blinkers + front KITT strip
