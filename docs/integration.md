# beat-flash-01 Integration

Owner: Drop-in Maintainers
Status: active
Last updated: 2026-06-21

## Load path

`app.py` loads the controller via `_load_beat_flash_controller_class()` →
`load_dropin_symbol('beat-flash-01/beat_flash_controller.py',
'BeatFlashController')` inside a `try/except` that sets `self._beat_flash =
None` on failure. The app starts cleanly when the drop-in is absent.

## Post chain + timing split

- **Timing** runs on the main thread: `self._beat_flash.update(dt, audio)` is
  called each frame (next to the other per-frame subsystem ticks) so a beat can
  arm a flash even while the pass is otherwise idle.
- **Rendering** runs in `App._apply_post_chain`, which appends `beat_flash`
  after `postfx` and `color_grade`. The strobe therefore composites last, on
  top of any colour grade. `is_active()` returns true only while a governed
  flash is visible, so the pass costs nothing at rest.

## Runtime surface

Registered as the `beat_flash` subsystem. Reachable via
`vj_api.get_subsystem('beat_flash')`:

- `toggle()`, `cycle_mode()`, `adjust_brightness(delta)`, `snapshot()`

The OSC bridge (osc-bridge-01) maps `/uv/beatflash/enable` and
`/uv/beatflash/intensity` to these (all still subject to the safety governor).

## Beat source

Driven by the `audio.beat` signal passed into `update`. It is "BPM-locked" in
that each (governed) beat produces one flash; `beat_division` strobes on every
Nth beat. It does not change any beat-detector constants, so no ADR update is
required.

## Independence

Self-contained GL (own fullscreen quad + shader). The GL-free
`FlashGovernor` owns all safety limits and is unit-tested without a context.
