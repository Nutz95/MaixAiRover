# Wiring

## Power

| Domain | Supply |
|--------|--------|
| Hiwonder VM | 5–15 V (12 V for JGB37-520) |
| Waveshare ESP | 7–13 V board supply **or** USB Type-C for flash/debug |
| MaixCAM2 | USB / own battery (3.7–5 V) |

Common **GND** across Maix ↔ ESP ↔ Hiwonder when they share a bus or UART.

## Motors — Waveshare ↔ Hiwonder (I2C)

| Waveshare IIC | Hiwonder |
|---------------|----------|
| SDA (GPIO32) | SDA |
| SCL (GPIO33) | SCL |
| GND | GND |

Do **not** connect Hiwonder header **5V** to ESP or Maix IO (3.3 V logic).

## Brain — MaixCAM2 ↔ ESP (UART)

| MaixCAM2 | Waveshare ESP32 |
|----------|-----------------|
| GND | GND |
| UART TX (TBD pin — prefer free UART on 6P / front header) | ESP RX |
| UART RX | ESP TX |

Level: **3.3 V**. Baud **115200**. Protocol: text lines (`SPEED` / `STOP` / …).

Until UART pins are finalized, smoke motors from PC USB serial:

```powershell
.\tools\flash_esp_coordinator.ps1 -Port COM9
python tools\drive_esp_coordinator.py --port COM9 --demo
```

## Later

- **STS3215** on Waveshare serial bus servo port (IDs TBD: pan/tilt cam + ToF mount)
- **WS2812**: 4 corner pairs (indicators) + front strip (KITT / ambiance) — GPIO TBD

## Legacy (do not use for product)

Maix A0/A1 direct to Hiwonder I2C — proven flaky; ESP path is the supported motor link.
