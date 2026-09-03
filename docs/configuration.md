# beat-flash-01 Configuration

Owner: Drop-in Maintainers
Status: active
Last updated: 2026-09-03

Keys live under `[beat_flash]` in `config.toml`. All have safe defaults; the
runtime governor hard-clamps every limit regardless of what is configured.

| Key | Type | Default | Notes |
| --- | --- | --- | --- |
| `enabled` | bool | `true` | Load the drop-in at all |
| `start_enabled` | bool | `false` | Live at boot; OFF by default for safety (use `Ctrl+Shift+Alt+B`) |
| `max_hz` | float | `3.0` | Flash rate cap; **hard-capped at 3.0** |
| `max_brightness` | float | `0.78` | Flash brightness; **hard-capped at 0.8** (bumped from `0.7` in 0.9.0 for a punchier default) |
| `flash_duration` | float | `0.22` | Seconds; clamped below the min inter-flash interval (bumped from `0.12` in 0.9.0 for a longer hold) |
| `beat_division` | int | `1` | Flash every Nth beat |
| `mode` | str | `full` | `full` \| `edge` \| `pulse` |
| `color` | list | `[1,1,1]` | Flash colour, RGB 0–1 |
| `beat_threshold` | float | `0.45` | Beat rising-edge trigger threshold |

Validation: `config_validator.py` warns when `max_hz > 3.0` (it will be
clamped), and flags bad types or an unknown `mode`.

A documented copy lives in `config.full.example.toml`.
