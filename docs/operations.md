# beat-flash-01 Operations

Owner: Drop-in Maintainers
Status: active
Last updated: 2026-06-21

## Purpose

Flash the frame on detected beats as a safety-governed, BPM-locked strobe.

## Lifecycle

- Loaded by `app.py` during GL setup (after color-grade) when present.
- Registered as the `beat_flash` subsystem + key handler.
- Advanced each frame via `update(dt, audio)` (arms flashes on beats);
  rendered via `App._apply_post_chain` when `is_active()` is true.
- Released via `destroy()` at shutdown.

## Live operation

- `Ctrl+Alt+B` — toggle on/off (off by default).
- `Ctrl+Alt+N` — cycle mode: full → edge → pulse.
- `Ctrl+Alt+-` / `Ctrl+Alt+=` — brightness ceiling down/up (still hard-capped).

## Safety

The `FlashGovernor` enforces ≤ 3 Hz, capped brightness, and non-overlapping
flashes. These ceilings are absolute and cannot be exceeded by config or any
control surface. When toggled off the envelope is reset immediately.
