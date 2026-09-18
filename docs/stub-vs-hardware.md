# Stub vs hardware (motion path)

## Target (phase 1C+)

| Mode | Meaning |
|------|---------|
| `uart.mode=stub` | Maix mixer runs; no bytes to ESP (HUD / tests) |
| `uart.mode=hardware` | Maix sends `SPEED`/`STOP` to ESP coordinator over UART |

## Legacy (being removed)

| Mode | Meaning |
|------|---------|
| `i2c.mode=stub` | Fake I2C bus inside Maix |
| `i2c.mode=hardware` | Maix I2C6 → Hiwonder directly — **unsupported** for product |

Until the UART client lands, keep Maix on `i2c.mode=stub` and exercise motors with:

```powershell
.\tools\flash_esp_coordinator.ps1 -Port COM9
python tools\drive_esp_coordinator.py --port COM9 --demo
```
