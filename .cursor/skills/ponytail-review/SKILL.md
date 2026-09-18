---
name: ponytail-review
description: >
  Diff review for over-engineering in the MaixCam2 × micro:bit Mecanum Rover
  project. Finds what to delete in changed files: reinvented MaixPy/mbed APIs,
  unneeded abstractions, dead flexibility. Use when the user says "review for
  over-engineering", "what can we delete", "is this over-engineered",
  "simplify review", or invokes /ponytail-review. Complements correctness
  review; hunts complexity only.
---

Review **changed files** for unnecessary complexity in
**Maixcam2-Keyestudio-MicrobitRover**. One line per finding: location, what to
cut, what replaces it. The diff's best outcome is getting shorter.

## Context

- **MaixCam** (`maixcam/`): MaixPy on Linux — `maix.*`, evdev, BlueZ. Not desktop CPython.
- **micro:bit** (`microbit/src/`): C++ firmware — UART protocol, mecanum mix, I2C motors. Keep lean and deterministic.
- **tools/**: PC test scripts only; do not grow into a second app.

Do not suggest moving BLE to micro:bit or motor control to MaixCam.

## Format

`L<line>: <tag> <what>. <replacement>.`, or `<file>:L<line>: ...` for multi-file diffs.

Tags: `delete:`, `stdlib:`, `maixpy:`, `native:`, `yagni:`, `shrink:`, `dup:` (see ponytail-audit skill for definitions).

`yagni:` does not apply to small single-caller modules that isolate a SOLID responsibility or keep classes under the project's size limit.

## Examples (this repo)

✅ `evdev_reader.py:L40: yagni: EvdevReaderFactory with one subclass. Inline until a second device type exists.`

✅ `joystick_frame_builder.py:L12: dup: SPEED_MAX redefined; use protocol_constants.SPEED_MAX.`

✅ `MecanumJoystickMapper.cpp:L88: shrink: four identical clamp branches. std::clamp or local macro, 4→1 lines.`

✅ `bluetooth_installer.py:L20: native: subprocess apt-get wrapper. document one-line shell in README instead.`

❌ `SerialSafe.h:L15: delete: checksum validation.` — trust-boundary validation is protected.

❌ `controller_mapping_engine.py:L30: yagni: deadzone mapping.` — hardware calibration, protected.

## Scoring

End with: `net: -<N> lines possible.`

Nothing to cut: `Lean already. Ship.`

## Boundaries

Complexity only. Never flag for deletion: UART framing/ACK, protocol validation,
mecanum mixer, motor driver, evdev mapping, camera HUD thread, config tuning
keys, `ponytail:` markers, or a single smoke test / assert self-check.

Does not apply fixes, only lists them.
"stop ponytail-review" or "normal mode": revert to verbose review style.
