# beat-flash-01 — BPM-Locked Strobe (Safety-Governed)

**Version 0.10.0**


A global post-FX pass that flashes the frame on detected beats, drawn last in
the post chain (on top of any colour grade). Loaded by default, but **inactive
at boot** (`start_enabled = false`) for photosensitivity safety — the operator
opts in with `Ctrl+Shift+Alt+B` or `start_enabled = true`.

## Safety first

All timing and intensity limits live in a GL-free `FlashGovernor` that hard-caps
the strobe regardless of config or external control:

- **≤ 3 Hz** flash rate (WCAG 2.x / ITU-R BT.1702 general-flash threshold).
  Beats faster than the cap are dropped.
- **Capped brightness** (≤ 0.8) so a flash never fully whites out the frame.
- **Non-overlapping flashes** — flash duration is clamped below the minimum
  inter-flash interval.

These ceilings cannot be raised via config, OSC, or MIDI.

## Controls

| Key | Action |
| --- | --- |
| `Ctrl+Shift+Alt+B` | Toggle the strobe on/off |
| `Ctrl+Shift+Alt+N` | Cycle flash mode (full / edge / pulse) |
| `Ctrl+Shift+Alt+-` | Brightness ceiling down |
| `Ctrl+Shift+Alt+=` | Brightness ceiling up (still capped) |

## Configuration

```toml
[beat_flash]
enabled = true          # load the drop-in (default true)
start_enabled = false   # OFF at boot (photosensitivity); Ctrl+Shift+Alt+B / set true
max_hz = 3.0            # hard-capped at 3.0 for safety
max_brightness = 0.78   # hard-capped at 0.8
flash_duration = 0.22   # seconds; clamped below the min inter-flash interval
beat_division = 1       # flash every Nth beat
mode = "full"           # full | edge | pulse
color = [1.0, 1.0, 1.0] # flash colour (RGB 0–1)
beat_threshold = 0.45   # beat signal rising-edge threshold
```

## Modes

- **full** — full-frame screen-blend flash.
- **edge** — flash weighted to the frame border (vignette strobe).
- **pulse** — brief overall brightness lift.

## Integration

Runs through `App._apply_post_chain` (postfx → color-grade → **beat-flash**).
Timing is advanced on the main thread via `update(dt, audio)`; `apply` renders
the current governed level. Registered as the `beat_flash` subsystem.

## Dependencies

Core only: `moderngl`, `numpy`. No new dependencies.

See `docs/` for operations, configuration, integration, and troubleshooting.

## Changelog

- **0.10.0** — Control Room panel (P1 of `docs/planning/control-room-drop-in-integration-plan-2026-09-05.md`): registered on the shared **FX** page from `set_vj_api()` — mode, max Hz, live level and brightness meters, TOGGLE / MODE / − / + buttons calling the same `toggle()` / `cycle_mode()` / `adjust_brightness()` as the `Ctrl+Shift+Alt+B/N/-/=` hotkeys and flashing the same text. Unregistered in `destroy()`.
- **0.9.0** — Stronger shipped defaults: `max_brightness` `0.7` → `0.78`
  (closer to the 0.8 safety ceiling) and `flash_duration` `0.12` → `0.22`
  seconds (longer hold, still well under the non-overlap clamp). The flash
  now reads as a clearly punchier hit on a typical beat instead of a token
  bump; `max_hz`, `beat_division`, and `mode` were already at their
  strongest useful settings (3.0 Hz cap, every beat, full-frame) so those
  were left untouched. All values remain fully overridable via
  `[beat_flash]` in `config.toml`.
- **0.8.0** — initial versioned release.
