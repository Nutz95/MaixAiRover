# MaixAiRover

MaixCAM2 mecanum rover: **Xbox + vision on the camera**, **hardware on a Waveshare ESP32**,
**motors on a Hiwonder I2C board**.

```
Xbox BLE ──► MaixCAM2 (mix / HUD / detection)
                 │ UART 115200
                 ▼
            Waveshare ESP32 (coordinator, OTA)
                 │ I2C 0x34
                 ▼
            Hiwonder 4-ch motors
```

First demo target: **Xbox teleop** over that chain.

## Quick start

### ESP coordinator (Waveshare)

```powershell
# Uses SOARM_WIFI_SSID / SOARM_WIFI_PASS from the system for OTA WiFi
.\tools\flash_esp_coordinator.ps1 -Port COM9 -Monitor
python tools\drive_esp_coordinator.py --port COM9 --demo
```

See [esp32/rover_coordinator/README.md](esp32/rover_coordinator/README.md).

### MaixCAM app

1. Bluetooth: [docs/bluetooth.md](docs/bluetooth.md) — **update Xbox firmware via Windows Xbox Accessories first**
2. Open `maixcam/roverMecanum/` in MaixVision (folder, not a lone file)
3. Deploy: `.\tools\deploy_rover_mecanum.ps1 -DeployOnly`

> Maix still has a legacy direct-I2C path (`i2c.mode`). Next milestone replaces it with a **UART client** to the ESP. Prefer `stub` on Maix until UART is wired.

## Host tests

```powershell
pip install -r tools\requirements-dev.txt
pytest -q
python tools\check_quality_guardrails.py
```

## Docs

| Doc | Topic |
|-----|--------|
| [docs/architecture.md](docs/architecture.md) | Layers |
| [docs/wiring.md](docs/wiring.md) | Power / UART / I2C |
| [docs/controls.md](docs/controls.md) | Xbox mapping |
| [docs/bluetooth.md](docs/bluetooth.md) | Xbox BLE pairing |
| [docs/roadmap.md](docs/roadmap.md) | Phased plan |
| [docs/plan.md](docs/plan.md) | Action plan (current) |
| [AGENTS.md](AGENTS.md) | Quality rules for agents |

## Package

`maixcam/roverMecanum/` is the MaixApp package.
