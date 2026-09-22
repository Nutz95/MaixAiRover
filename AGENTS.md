# AGENTS.md — MaixAiRover

Guidance for humans and coding agents working in this repository.

## Product context

```
MaixCAM2 (Xbox BLE, vision, strategy)
 │ drive_backend=esp:    UART4/UART2 → Waveshare ESP ×2
 │ drive_backend=yahboom: USB Host → Yahboom ROS (CH340)
 ▼
Mecanum wheels
```

- **MaixCAM2:** controller + detection + heavy compute; mecanum mix; backend switch in `config.json`.
- **ESP32 front/rear:** same firmware; local motor pair + PID; USB + OTA (`maixairover-front` / `maixairover-rear`).
- **Yahboom STM32:** pre-flashed Rosmaster; `set_motor` + IMU auto-report — see `docs/yahboom.md`.
- **Hiwonder:** retired.
- WiFi for OTA: system env `SOARM_WIFI_SSID` / `SOARM_WIFI_PASS`.
- Device IPs: `esp32/rover_coordinator/devices.json`.

Shipable MaixApp: `maixcam/roverMecanum/`. ESP firmware: `esp32/rover_coordinator/`.

## Non-negotiable quality rules

These override ponytail “fewest files” when they conflict. Ponytail still applies to **features** (YAGNI).

1. **SOLID** — one responsibility per class; depend on ports/interfaces, not concrete hardware.
2. **1 class = 1 file.**
3. **Each file &lt; 400 lines** of code.
4. **Each class &lt; 30 methods.**
5. **Every public class and public method has a docstring.**
6. **No `getattr` / `setattr`.** Use explicit attributes and typed contracts.
7. **No tuples as payloads.** Prefer dataclasses (or similar) with named fields.
8. **No anonymous dicts as structs.** If JSON is loaded, map it into typed models immediately.
9. **Unit-testable core:** mixer, mapping, motion logic must run without MaixPy / without ESP hardware (inject transports).
10. **Thermo-nuclear bar:** prefer deleting complexity over rearranging it; no spaghetti branches in shared paths; no thin wrappers.

## Package layout

Shipable MaixApp lives in `maixcam/roverMecanum/` (`main.py` + `app.yaml` + icons + `lib/`).

## Docs

Update `docs/` when architecture, wiring, controls, or flash flow change.

## Tests

Host: `pytest` from repo root (`tools/requirements-dev.txt`).
ESP smoke: `tools/drive_esp_coordinator.py` + `tools/flash_esp_coordinator.ps1`.
