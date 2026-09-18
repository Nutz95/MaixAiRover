---
name: ponytail-audit
description: >
  Whole-repo audit for over-engineering in the MaixCam2 × micro:bit Mecanum
  Rover project. Scans maixcam/, microbit/, and tools/ for bloat: dead code,
  YAGNI abstractions, hand-rolled helpers MaixPy or mbed already cover. Use
  when the user says "audit this codebase", "audit for over-engineering",
  "what can I delete from this repo", "find bloat", "ponytail-audit", or
  "/ponytail-audit". One-shot report, does not apply fixes.
---

Repo-wide ponytail-review for **Maixcam2-Keyestudio-MicrobitRover**. Scan the
whole tree, rank findings biggest cut first.

## Architecture (do not break)

```
Xbox (BLE) → MaixCam2 (MaixPy Python, evdev, HUD) ── UART 115200 ──► micro:bit V2 (C++, motors)
```

| Path | Role | Audit lens |
|------|------|------------|
| `maixcam/roverMecanum/` | Packaged MaixPy app — Xbox → UART | MaixPy + Linux evdev, not desktop Python |
| `maixcam/*.py` | Standalone dev / test scripts | Keep if referenced in README or deploy; cut if orphaned |
| `microbit/src/` | Real-time firmware — protocol, mecanum mix, I2C motors | Embedded: lean, deterministic, no speculative layers |
| `tools/` | PC PowerShell + Python test harness | Minimal scripts; no duplicate of the full app |
| `microbit/PROTOCOL*.md` | Protocol spec | Not code bloat |

**Intentional split:** Bluetooth/HID/evdev stay on MaixCam (Linux). Motor
timing stays on micro:bit. Never suggest moving BLE to the nRF52 or vision to
the micro:bit as a "simplification".

## Scan order

1. `maixcam/roverMecanum/lib/` — most modules, highest merge/cut surface
2. `maixcam/roverMecanum/main.py`, `config.json`
3. `maixcam/` root scripts (`maixcam_*.py`, `bluetooth_*.py`, `rover_uart.py`)
4. `microbit/src/` — `.cpp` / `.h`
5. `tools/` — `test_rover_menu.py`, `*.ps1`, `requirements.txt`

Skip: `resources/`, `.pio/`, `__pycache__/`, build artifacts, images, docs
unless a doc duplicates logic that should live in one place.

## Tags

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing Python/C++ stdlib ships. Name the function. **MaixPy only:** flag only if the API exists on-device (see boundaries).
- `maixpy:` custom wrapper around `maix.*` that only delegates. Name the built-in.
- `native:` Linux kernel / BlueZ / `bluetoothctl` / evdev feature covers it; mbed/micro:bit API covers it on firmware.
- `yagni:` abstraction with one implementation, config key never set, layer with one caller.
- **Not yagni:** small modules or files with a single caller when they isolate a SOLID responsibility or keep classes under the project's size limit — that split is intentional for readability (humans and coding agents).
- `shrink:` same logic, fewer lines. Show the shorter form.
- `dup:` same constants or framing logic duplicated across MaixCam Python and micro:bit C++ without a documented reason.

## Hunt

**MaixCam (Python / MaixPy)**

- Dependencies or patterns that assume full CPython stdlib on a PC — MaixPy is not desktop Python.
- `evdev_*` modules that only forward to each other; candidates to inline or merge.
- Config indirection (`config_store`, `paths`) deeper than needed for one JSON file.
- HUD/camera helpers that reimplement `maix.camera`, `maix.display`, or `maix.image` one-liners.
- Bluetooth helpers that shell out when `bluetoothctl` / BlueZ already does the job in fewer lines. **bleak is not used** — scan/pair/connect go through BlueZ only.
- Standalone `maixcam/*.py` scripts superseded by `roverMecanum/` — check README and deploy script references before tagging `delete:`.

**micro:bit (C++ / PlatformIO)**

- Virtual interfaces / templates with a single implementation.
- Parser or dispatcher layers above `ProtocolParser` / `CommandDispatcher` with no second consumer.
- Motor or serial wrappers that only pass through to `MotorDriver` / `SerialRover`.
- Duplicate preset/command tables vs `Protocol.h`.
- Heap churn, `String` concatenation, or heavy STL in the UART hot path — `shrink:` toward stack buffers and fixed arrays.

**tools/**

- Logic copied from `roverMecanum/lib/` that could import or share one module (only if PC Python can share without MaixPy imports).
- Unused CLI flags, menu branches, or dependencies in `requirements.txt`.

## Protected (never flag for deletion)

- UART framing: sync `0xAA`, checksum, ACK `0x55 + CMD`, 12-byte joystick frame `0x30`
- `protocol_constants.py` ↔ `Protocol.h` alignment (flag `dup:` if diverged, not `delete:`)
- Mecanum mixer (`MecanumJoystickMapper`), motor I2C (`MotorDriver`), dual serial (`SerialRover`, P1/P2 + USB)
- Input validation at protocol trust boundaries (`SerialSafe`, checksum checks, frame length)
- Drive tuning: `deadzone_percent`, `axis_curve`, `axis_expo`, `mapping.axes`, `max_speed`
- evdev axis mapping, Xbox layout tables, `controller_mapping_engine` — real hardware needs calibration
- `camera_preview_service` capture thread — preview + HUD is a core feature
- Bluetooth pair/connect flow on MaixCam
- `tools/run_test_rover.ps1` / `test_rover_menu.py` — PC debug path documented in README
- Comment markers `# ponytail:` / `// ponytail:` — documented shortcuts; list under ponytail-debt, do not delete
- One small smoke test or assert-based self-check per non-trivial module

## Output

Group by tree (`maixcam/`, `microbit/`, `tools/`). One line per finding, ranked
within each group, biggest cut first:

`<tag> <what to cut>. <replacement>. [path:line]`

End with:

```
net: -<N> lines, -<M> deps possible.
```

Nothing to cut: `Lean already. Ship.`

## Boundaries

Complexity only — correctness bugs, security holes, timing, and motor safety go
to a normal review. Lists findings, applies nothing. One-shot.

"stop ponytail-audit" or "normal mode" to revert.
