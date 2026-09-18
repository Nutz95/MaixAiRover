# Maix AI Rover (MaixCAM2 package)

Xbox BLE teleop for a Hiwonder mecanum chassis over I2C6.

Default `config.json` uses `"i2c": { "mode": "hardware" }` on I2C6 (A0/A1 → Hiwonder `0x34`). Use `"stub"` if the motor board is unplugged. The HUD motor pad jogs each wheel without Xbox.

See repo docs: `docs/architecture.md`, `docs/stub-vs-hardware.md`, `docs/controls.md`.
