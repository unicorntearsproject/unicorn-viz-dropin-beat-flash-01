"""Optional config validation for the beat-flash-01 drop-in.

Surfaces config that *requests* unsafe values.  Note the runtime governor
hard-clamps regardless; these messages just tell the operator their requested
value was reduced for safety.
"""
from __future__ import annotations

from typing import Any

_NUMERIC = ('max_hz', 'max_brightness', 'flash_duration', 'beat_threshold')


def validate_config(config_data: dict[str, Any]) -> list[str]:
    """Validate the ``[beat_flash]`` section, returning any error strings."""
    errors: list[str] = []
    section = config_data.get('beat_flash')
    if section is None:
        return errors
    if not isinstance(section, dict):
        return ['[beat_flash] must be a table']

    for key in ('enabled', 'start_enabled'):
        if key in section and not isinstance(section[key], bool):
            errors.append(f'[beat_flash] {key} must be a boolean')

    for key in _NUMERIC:
        if key in section and not isinstance(section[key], (int, float)):
            errors.append(f'[beat_flash] {key} must be a number')

    if 'beat_division' in section and not isinstance(section['beat_division'], int):
        errors.append('[beat_flash] beat_division must be an integer')

    max_hz = section.get('max_hz')
    if isinstance(max_hz, (int, float)) and float(max_hz) > 3.0:
        errors.append(
            '[beat_flash] max_hz exceeds the 3 Hz photosensitivity safety cap '
            '(it will be clamped to 3.0)'
        )

    mode = section.get('mode')
    if mode is not None and str(mode).lower() not in ('full', 'edge', 'pulse'):
        errors.append("[beat_flash] mode must be one of: full, edge, pulse")

    return errors
