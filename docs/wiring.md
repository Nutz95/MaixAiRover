# Wiring

## Power

| Domain | Supply |
|--------|--------|
| Waveshare ESP board | **7–13 V** on XH2.54 (required for motors; USB alone brownouts under load) |
| MaixCAM2 | USB / own battery |
| Motors | Powered by each Waveshare motor rail (same board supply) |

Common **GND** across Maix ↔ each ESP when UART is wired.

## Motors — Waveshare onboard TB6612 (same on front and rear)

Each board drives **its local left/right** only (`m1/m2` in protocol). Maix maps FL/FR → front board, RL/RR → rear board.

| Channel | Role on that board | Encoder | TB6612 |
|---------|--------------------|---------|--------|
| Motor B | Left | IO27 (B_C1), IO16 (B_C2) | PWMB=26, BIN1=22, BIN2=23 |
| Motor A | Right (inverted) | IO34 (A_C1), IO35 (A_C2) | PWMA=25, AIN1=21, AIN2=17 |

Mechanical model (firmware): **11 PPR × 4 quadrature × 56:1 gear**, max **178 RPM** wheel. Closed-loop `SPEED` uses a 100 Hz PID in RPM space.

## Brain — MaixCAM2 ↔ dual ESP

UART0 (USB / silk `RX` / 40PIN TX) proved unreliable for Maix→ESP.
Firmware uses **ESP32 UART2** on the aux 10-pin (red-circle header) on **each** Waveshare:

### Front — Maix UART4

| MaixCAM2 (6P latéral) | Waveshare silk | ESP32 |
|----------------------|----------------|-------|
| GND | **GND** (next to IO4/IO5) | GND |
| **A21** UART4_TX | **IO4** | UART2 RX |
| **A22** UART4_RX | **IO5** | UART2 TX |

`config.json` → `esp.front.uart_port = "uart4"`.

### Rear — Maix UART2 (façade)

| MaixCAM2 (front header) | Waveshare silk | ESP32 |
|-------------------------|----------------|-------|
| GND | **GND** | GND |
| **B0** UART2_TX | **IO4** | UART2 RX |
| **B1** UART2_RX | **IO5** | UART2 TX |

`config.json` → `esp.rear.uart_port = "uart2"`.

Level **3.3 V**. Baud **115200**.

Do **not** use IO27 / IO16 (motor B encoders). LIDAR PH2.0 is RX-only (`CP_RX`).

### USB-C backup (UART0 CP2102)

Maix USB mode **Host** → Waveshare USB-C (`EspUsbClient`). Separate from IO4/IO5 link.

### What not to use

| Pins | Why |
|------|-----|
| IO12–IO15 | MicroSD SPI |
| IO27 / IO16 | Motor B encoders |
| UART0 silk RX / 40PIN TX alone | Shared with CP2102; Maix→ESP flaky |

## OTA / flash

| Board | PlatformIO env | OTA hostname | IP file |
|-------|----------------|--------------|---------|
| Front | `waveshare_front` / `_ota` | `maixairover-front` | `devices.json` → `front` |
| Rear | `waveshare_rear` / `_ota` | `maixairover-rear` | `devices.json` → `rear` |

```powershell
.\tools\flash_esp_coordinator.ps1 -Board rear -Port COM11
.\tools\flash_esp_coordinator.ps1 -Board front -Ota
.\tools\flash_esp_coordinator.ps1 -Board both -Ota
```

WiFi secrets: `SOARM_WIFI_SSID` / `SOARM_WIFI_PASS` (same AP for both boards).

## Commands (USB Serial / aux UART / WiFi :2333)

```
PING | INIT | STOP | SPEED fl fr rl rr | PWM | ENC | BAT | SCAN | WIFI | HELP
bin: SYNC=0xA5 TYPE LEN PAYLOAD CRC8 (PING/STOP/SPEED/PWM/TELEM)
```

`BAT` → `ERR` (no Hiwonder ADC). `SCAN` → `OK SCAN 1 motor=1 front=2`.

## PC smoke

```powershell
.\tools\flash_esp_coordinator.ps1 -Board front -Port COMx
python tools\drive_esp_coordinator.py --port COMx
# then: SPEED 20 20 0 0
```

## Servos (later)

STS bus on each Waveshare (camera set vs TOF set). Maix forwards commands over the same UART links; assignment TBD in config.
