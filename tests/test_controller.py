"""Controller tests for beat-flash-01 (GL assertions skip without headless GL)."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest

_MOD = Path(__file__).resolve().parents[1] / 'beat_flash_controller.py'
_spec = importlib.util.spec_from_file_location('beat_flash_controller_test', _MOD)
ctrl_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ctrl_mod
_spec.loader.exec_module(ctrl_mod)
BeatFlashController = ctrl_mod.BeatFlashController


@pytest.fixture
def ctx():
    moderngl = pytest.importorskip('moderngl')
    try:
        c = moderngl.create_standalone_context()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f'no headless GL context: {exc}')
    yield c
    c.release()


def _beat(level: float) -> types.SimpleNamespace:
    return types.SimpleNamespace(beat=level, bass=0.0, mid=0.0, treble=0.0)


def test_disabled_by_default(ctx) -> None:
    c = BeatFlashController(ctx, 16, 16, {})
    assert c.enabled is False
    assert c.is_active() is False
    c.destroy()


def test_default_intensity_is_the_punchier_0_9_0_baseline(ctx) -> None:
    """Un-overridden defaults should ship at the stronger 0.9.0 values.

    Peak brightness 0.7 -> 0.78 and hold time 0.12s -> 0.22s (see README
    changelog); both stay comfortably under the governor's absolute safety
    ceilings (0.8 brightness, non-overlapping-flash duration clamp).
    """
    c = BeatFlashController(ctx, 16, 16, {})
    assert c._governor.max_brightness == pytest.approx(0.78)
    assert c._governor._flash_duration == pytest.approx(0.22)
    c.destroy()


def test_update_arms_flash_when_enabled(ctx) -> None:
    c = BeatFlashController(ctx, 16, 16, {'start_enabled': True})
    c.update(0.01, _beat(1.0))
    assert c.is_active() is True
    c.destroy()


def test_disabled_update_does_not_arm(ctx) -> None:
    c = BeatFlashController(ctx, 16, 16, {'enabled': False})
    c.update(0.01, _beat(1.0))
    assert c.is_active() is False
    c.destroy()


def test_toggle_resets_on_disable(ctx) -> None:
    c = BeatFlashController(ctx, 16, 16, {'start_enabled': True})
    c.update(0.01, _beat(1.0))
    assert c.is_active() is True
    c.toggle()  # disable
    assert c.is_active() is False
    c.destroy()


def test_cycle_mode(ctx) -> None:
    c = BeatFlashController(ctx, 16, 16, {'start_enabled': True, 'mode': 'full'})
    assert c.mode == 'full'
    assert c.cycle_mode() == 'edge'
    assert c.cycle_mode() == 'pulse'
    assert c.cycle_mode() == 'full'
    c.destroy()


def test_flash_brightens_pixels(ctx) -> None:
    import moderngl
    src = ctx.texture((8, 8), 4)
    src.filter = (moderngl.NEAREST, moderngl.NEAREST)
    sf = ctx.framebuffer(color_attachments=[src])
    sf.use()
    ctx.clear(0.2, 0.2, 0.2, 1.0)
    dst = ctx.texture((8, 8), 4)
    df = ctx.framebuffer(color_attachments=[dst])

    c = BeatFlashController(ctx, 8, 8, {'start_enabled': True, 'mode': 'full', 'max_brightness': 0.6})
    c.update(0.001, _beat(1.0))  # arm a flash
    assert c.apply(src, df, 0.001, 0.0, 0.0, 0.0, 0.0) is True
    px = np.frombuffer(df.read(components=4), dtype=np.uint8).reshape(8, 8, 4)[0, 0]
    # Screen-blend with a white flash brightens the grey source.
    assert int(px[0]) > 51  # 0.2 * 255
    c.destroy()
