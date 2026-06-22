"""BPM-locked strobe / flash post pass with a photosensitivity safety governor.

A global post-FX pass (drawn last, on top of any colour grade) that flashes the
frame on detected beats.  All rate/intensity limits live in the GL-free
:class:`FlashGovernor` (see ``governor.py``) so neither the renderer nor any
external control surface can drive the strobe past safe bounds (≤ 3 Hz, capped
brightness, non-overlapping flashes).

Timing is advanced on the main thread via :meth:`update` (so a beat can arm a
flash even when the pass is otherwise idle); :meth:`apply` only renders the
current governor level.  Shares the post-chain contract with postfx-01 /
color-grade-01: ``apply(src_tex, dst_fbo, dt, bass, mid, treble, beat)``.

Disabled by default — the operator must opt in (``Ctrl+Shift+Alt+B`` or config).
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

import moderngl
import numpy as np

log = logging.getLogger(__name__)

_GOV_PATH = Path(__file__).resolve().parent / 'governor.py'
_gov_spec = importlib.util.spec_from_file_location('beat_flash_governor', _GOV_PATH)
if _gov_spec is None or _gov_spec.loader is None:  # pragma: no cover - import guard
    raise ImportError(f'beat-flash-01: failed to load {_GOV_PATH}')
_gov = importlib.util.module_from_spec(_gov_spec)
sys.modules[_gov_spec.name] = _gov
_gov_spec.loader.exec_module(_gov)
FlashGovernor = _gov.FlashGovernor


DROPIN_CAPABILITIES = {
    'name': 'beat_flash',
    'class_symbol': 'BeatFlashController',
    'subsystem_name': 'beat_flash',
    'key_handler_attr': 'handle_key',
}

HELP_ENTRIES = [
    ('Beat Flash', 'Ctrl+Shift+Alt+B', 'Toggle BPM-locked strobe (safety-governed)'),
    ('Beat Flash', 'Ctrl+Shift+Alt+N', 'Cycle flash mode (full / edge / pulse)'),
    ('Beat Flash', 'Ctrl+Shift+Alt+-', 'Flash brightness down'),
    ('Beat Flash', 'Ctrl+Shift+Alt+=', 'Flash brightness up'),
]

_MODES = ('full', 'edge', 'pulse')

_VERT = """
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

_FRAG = """
#version 330
// Beat-flash overlay pass.
// Uniforms:
//   tex     — source frame (unit 0)
//   uLevel  — governed flash brightness [0, max_brightness]
//   uColor  — flash colour
//   uMode   — 0 full screen-blend, 1 edge vignette, 2 brightness pulse
// Produces fragColor = source with the flash composited on top.

uniform sampler2D tex;
uniform float uLevel;
uniform vec3  uColor;
uniform int   uMode;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec3 src = texture(tex, v_uv).rgb;
    vec3 outc = src;
    float lvl = clamp(uLevel, 0.0, 1.0);
    if (uMode == 1) {
        // Edge-weighted flash: strongest at the frame border.
        vec2 d = abs(v_uv - 0.5) * 2.0;
        float edge = clamp(max(d.x, d.y), 0.0, 1.0);
        edge = smoothstep(0.55, 1.0, edge);
        vec3 flash = uColor * (lvl * edge);
        outc = 1.0 - (1.0 - src) * (1.0 - flash);
    } else if (uMode == 2) {
        // Brightness pulse: lift overall exposure toward the flash colour.
        outc = src * (1.0 + lvl) + uColor * (lvl * 0.25);
    } else {
        // Full-frame screen blend + a small additive lift so the flash still
        // reads clearly over already-bright scenes (screen blend alone barely
        // moves near-white pixels).
        vec3 flash = uColor * lvl;
        vec3 screen = 1.0 - (1.0 - src) * (1.0 - flash);
        outc = screen + uColor * (lvl * 0.18);
    }
    fragColor = vec4(clamp(outc, 0.0, 1.0), 1.0);
}
"""


class BeatFlashController:
    """Runtime controller for the BPM-locked, safety-governed strobe pass."""

    NAME = 'Beat Flash'

    def __init__(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        cfg: dict[str, Any] | None = None,
    ) -> None:
        self._ctx = ctx
        self._width = width
        self._height = height
        self._cfg = dict(cfg or {})
        self._vj_api: Any = None

        # ``enabled`` gates loading (host); ``start_enabled`` decides whether the
        # strobe is live at boot.  Defaults OFF for photosensitivity safety — the
        # operator must opt in explicitly (Ctrl+Shift+Alt+B or start_enabled).
        self.enabled = bool(self._cfg.get('start_enabled', False))
        self._governor = FlashGovernor(
            max_hz=float(self._cfg.get('max_hz', 3.0)),
            max_brightness=float(self._cfg.get('max_brightness', 0.7)),
            flash_duration=float(self._cfg.get('flash_duration', 0.12)),
            beat_division=int(self._cfg.get('beat_division', 1)),
            beat_threshold=float(self._cfg.get('beat_threshold', 0.45)),
        )
        mode = str(self._cfg.get('mode', 'full')).lower()
        self._mode_index = _MODES.index(mode) if mode in _MODES else 0
        color = self._cfg.get('color', [1.0, 1.0, 1.0])
        self._color = self._parse_color(color)

        self._prog = ctx.program(vertex_shader=_VERT, fragment_shader=_FRAG)
        verts = np.array([-1, -1, -1, 1, 1, -1, 1, 1], dtype=np.float32)
        self._vbo = ctx.buffer(verts)
        self._vao = ctx.vertex_array(self._prog, [(self._vbo, '2f', 'in_vert')])

    @staticmethod
    def _parse_color(raw: Any) -> tuple[float, float, float]:
        try:
            r, g, b = (float(x) for x in raw[:3])
            return (
                float(np.clip(r, 0.0, 1.0)),
                float(np.clip(g, 0.0, 1.0)),
                float(np.clip(b, 0.0, 1.0)),
            )
        except Exception:
            return (1.0, 1.0, 1.0)

    # ------------------------------------------------------------- public API
    def set_vj_api(self, api: Any) -> None:
        self._vj_api = api

    def is_active(self) -> bool:
        """True only while a governed flash is visible (skips the pass at rest)."""
        return self.enabled and self._governor.level > 3e-3

    @property
    def mode(self) -> str:
        return _MODES[self._mode_index]

    @property
    def debug_summary(self) -> str:
        return (
            f'en={int(self.enabled)} mode={self.mode} '
            f'lvl={self._governor.level:.2f} maxHz={self._governor.max_hz:.1f}'
        )

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if not self.enabled:
            self._governor.reset()
        return self.enabled

    def cycle_mode(self) -> str:
        self._mode_index = (self._mode_index + 1) % len(_MODES)
        return self.mode

    def adjust_brightness(self, delta: float) -> float:
        """Nudge the brightness ceiling (still hard-capped by the governor)."""
        return self._governor.set_max_brightness(self._governor.max_brightness + delta)

    def snapshot(self) -> dict[str, Any]:
        return {
            'enabled': self.enabled,
            'mode': self.mode,
            'level': self._governor.level,
            'max_hz': self._governor.max_hz,
            'max_brightness': self._governor.max_brightness,
        }

    # --------------------------------------------------------------- app hooks
    def update(self, dt: float, audio: Any) -> None:
        """Advance the strobe governor on the main thread (beat → flash)."""
        beat = float(getattr(audio, 'beat', 0.0) or 0.0)
        self._governor.update(dt, beat, active=self.enabled)

    def apply(
        self,
        src_tex: moderngl.Texture,
        dst_fbo: moderngl.Framebuffer,
        dt: float,            # noqa: ARG002 - shared post-chain signature
        bass: float,          # noqa: ARG002
        mid: float,           # noqa: ARG002
        treble: float,        # noqa: ARG002
        beat: float,          # noqa: ARG002
    ) -> bool:
        """Composite the current governed flash over ``src_tex`` into ``dst_fbo``."""
        if not self.is_active():
            return False
        dst_fbo.use()
        self._ctx.viewport = (0, 0, dst_fbo.size[0], dst_fbo.size[1])
        self._ctx.clear(0.0, 0.0, 0.0, 1.0)
        src_tex.use(location=0)
        self._prog['tex'].value = 0
        self._prog['uLevel'].value = float(self._governor.level)
        self._prog['uColor'].value = self._color
        self._prog['uMode'].value = self._mode_index
        self._vao.render(moderngl.TRIANGLE_STRIP)
        return True

    def resize(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    # ------------------------------------------------------------- input/teardown
    def handle_key(self, sym: int, mod: int) -> 'str | None | bool':
        """Handle Ctrl+Shift+Alt beat-flash hotkeys; return status string when handled."""
        import sdl2  # noqa: PLC0415
        if not (
            (mod & sdl2.KMOD_CTRL)
            and (mod & sdl2.KMOD_ALT)
            and (mod & sdl2.KMOD_SHIFT)
        ):
            return False
        if sym == sdl2.SDLK_b:
            on = self.toggle()
            return f'Beat flash {"on" if on else "off"} ({self.mode})'
        if sym == sdl2.SDLK_n:
            return f'Beat flash mode: {self.cycle_mode()}'
        if sym == sdl2.SDLK_MINUS:
            return f'Flash brightness {self.adjust_brightness(-0.05):.2f}'
        if sym == sdl2.SDLK_EQUALS:
            return f'Flash brightness {self.adjust_brightness(0.05):.2f}'
        return False

    def destroy(self) -> None:
        try:
            self._vao.release()
            self._vbo.release()
            self._prog.release()
        except Exception as exc:
            log.warning('beat-flash: destroy error: %s', exc)
