# AGENTS.md — MaixAiRover

Guidance for humans and coding agents working in this repository.

## Product context

```
MaixCAM2 (Xbox BLE, vision, strategy)
    │ UART 115200 (text protocol → ESP)
    ▼
Waveshare ESP32 General Driver (rover_coordinator)
    │ I2C @ 0x34
    ▼
Hiwonder 4-channel encoder motor board
```

- **MaixCAM2:** controller + detection + heavy compute; does **not** own motor I2C long-term.
- **ESP32:** hardware coordinator (motors now; STS3215 servos + WS2812 later); USB + **OTA** flash.
- **Hiwonder:** motors only.
- WiFi for OTA: system env `SOARM_WIFI_SSID` / `SOARM_WIFI_PASS` (bake at compile via PlatformIO).

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
