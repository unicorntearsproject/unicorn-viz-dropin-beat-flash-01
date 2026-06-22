# beat-flash-01 Troubleshooting

Owner: Drop-in Maintainers
Status: active
Last updated: 2026-06-21

## No flashing

- Confirm the strobe is switched on: `[beat_flash] start_enabled = true` (OFF by
  default for safety) or press `Ctrl+Shift+Alt+B`.
- The strobe only fires on beats — confirm the audio pipeline is detecting
  beats (the HUD/Auto-VJ status shows beat activity).
- `beat_division > 1` reduces the flash rate (every Nth beat).

## Flashing feels too weak / too strong

- Adjust `max_brightness` (or `Ctrl+Shift+Alt+-` / `Ctrl+Shift+Alt+=`). It is hard-capped at
  0.8 for safety and cannot be raised beyond that.

## I set max_hz above 3 but it isn't faster

This is intentional. `max_hz` is hard-capped at 3 Hz (photosensitivity safety,
WCAG/ITU). The config validator warns when a higher value is requested. Beats
arriving faster than the cap are dropped.

## Choosing a mode

- `full` — whole-frame strobe (most intense; use a lower `max_brightness`).
- `edge` — border-weighted; less central glare.
- `pulse` — subtle brightness lift; gentlest option.

## Tests

`tests/test_governor.py` proves the rate/brightness caps hold under abusive
input (no GL needed). `tests/test_controller.py` exercises the GL pass and
skips when no headless context is available.
