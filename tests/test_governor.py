"""Safety-governor tests for beat-flash-01 (GL-free)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GOV = Path(__file__).resolve().parents[1] / 'governor.py'
_spec = importlib.util.spec_from_file_location('beat_flash_governor_test', _GOV)
gov = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gov)
FlashGovernor = gov.FlashGovernor


def _drive(g: "FlashGovernor", *, seconds: float, dt: float, beat_hz: float) -> int:
    """Drive the governor with a beat at ``beat_hz`` and count flash onsets."""
    flashes = 0
    prev = 0.0
    t = 0.0
    next_beat = 0.0
    steps = int(seconds / dt)
    for _ in range(steps):
        beat = 0.0
        if beat_hz > 0 and t >= next_beat:
            beat = 1.0
            next_beat += 1.0 / beat_hz
        level = g.update(dt, beat)
        if level > prev and prev <= 1e-6:  # rising from rest = a new flash
            flashes += 1
        prev = level
        t += dt
    return flashes


def test_max_hz_is_hard_capped_at_3() -> None:
    g = FlashGovernor(max_hz=100.0)  # request absurdly high
    assert g.max_hz == 3.0
    assert g.min_interval == pytest.approx(1.0 / 3.0)


def test_brightness_is_hard_capped() -> None:
    g = FlashGovernor(max_brightness=5.0)
    assert g.max_brightness <= 0.8
    assert g.set_max_brightness(100.0) <= 0.8


def test_rate_governor_drops_excess_flashes() -> None:
    # Beats at 12 Hz must not produce more than ~3 flashes/sec.
    g = FlashGovernor(max_hz=3.0, max_brightness=0.5, flash_duration=0.1)
    flashes = _drive(g, seconds=5.0, dt=1.0 / 240.0, beat_hz=12.0)
    # Allow a small boundary tolerance over 5 s at 3 Hz (15).
    assert flashes <= 16, f'governor allowed {flashes} flashes (>3 Hz)'


def test_level_never_exceeds_max_brightness() -> None:
    g = FlashGovernor(max_hz=3.0, max_brightness=0.4)
    peak = 0.0
    t = 0.0
    for _ in range(2000):
        peak = max(peak, g.update(1 / 240.0, 1.0 if (t % 0.33) < 0.01 else 0.0))
        t += 1 / 240.0
    assert peak <= 0.4 + 1e-6


def test_disabled_active_flag_only_decays() -> None:
    g = FlashGovernor(max_hz=3.0, max_brightness=0.5)
    # Arm a flash, then drive inactive — it should decay to 0 and not re-arm.
    g.update(0.01, 1.0)
    assert g.level > 0
    for _ in range(200):
        g.update(0.01, 1.0, active=False)
    assert g.level == 0.0


def test_beat_division_reduces_flash_count() -> None:
    g1 = FlashGovernor(max_hz=3.0, beat_division=1)
    g2 = FlashGovernor(max_hz=3.0, beat_division=2)
    # Beats at 2 Hz (under the cap) so the cap doesn't mask the division effect.
    f1 = _drive(g1, seconds=6.0, dt=1 / 240.0, beat_hz=2.0)
    f2 = _drive(g2, seconds=6.0, dt=1 / 240.0, beat_hz=2.0)
    assert f2 < f1


def test_flash_duration_clamped_below_min_interval() -> None:
    g = FlashGovernor(max_hz=3.0, flash_duration=10.0)
    # Duration must be below the min interval so flashes never overlap.
    assert g._flash_duration <= g.min_interval
