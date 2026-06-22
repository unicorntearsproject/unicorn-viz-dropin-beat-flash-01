# beat-flash-01 — BPM-Locked Strobe (Safety-Governed)

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
max_brightness = 0.7    # hard-capped at 0.8
flash_duration = 0.12   # seconds; clamped below the min inter-flash interval
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
