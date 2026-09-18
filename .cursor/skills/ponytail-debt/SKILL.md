---
name: ponytail-debt
description: >
  Harvest every `ponytail:` comment in the MaixCam2 × micro:bit rover repo
  into a debt ledger. Use when the user says "ponytail debt", "/ponytail-debt",
  "what did ponytail defer", "list the shortcuts", "ponytail ledger", or "what
  did we mark to do later". One-shot report, changes nothing.
---

Collect deliberate `ponytail:` shortcuts across **Maixcam2-Keyestudio-MicrobitRover**.

## Scan

Search Python (`# ponytail:`) and C++ (`// ponytail:`) comments. Skip
`resources/`, `.pio/`, `__pycache__/`, build output.

Primary trees: `maixcam/`, `microbit/src/`, `tools/`.

## Output

One row per marker, grouped by file:

`<file>:<line> — <what was simplified>. ceiling: <limit>. upgrade: <trigger>.`

Flag `no-trigger` when the comment names no upgrade path.

End with `<N> markers, <M> with no trigger.` Nothing found: `No ponytail: debt. Clean ledger.`

## Boundaries

Reads and reports only. To persist, write `PONYTAIL-DEBT.md` only if the user asks.
"stop ponytail-debt" or "normal mode" to revert.
