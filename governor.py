"""Photosensitivity-safety governor for the beat-flash-01 strobe.

GL-free and fully unit-testable.  Encapsulates *all* the timing and intensity
limits so neither the renderer nor any external control surface (OSC/MIDI) can
drive the strobe past safe bounds:

- **Flash rate** is hard-capped at ``_ABS_MAX_HZ`` (≤ 3 Hz, the WCAG 2.x /
  ITU-R BT.1702 general-flash threshold).  Beats arriving faster than the cap
  are dropped.
- **Brightness** is hard-capped at ``_ABS_MAX_BRIGHTNESS`` so a flash can never
  fully white-out the frame.
- **Flash duration** is clamped below the minimum inter-flash interval so
  consecutive flashes never overlap into an effectively higher rate.

The governor exposes a single :attr:`level` (0 → max-brightness) that the
renderer multiplies into its flash overlay.
"""
from __future__ import annotations

# Absolute safety ceilings — config may lower these but never raise them.
_ABS_MAX_HZ = 3.0
_ABS_MAX_BRIGHTNESS = 0.8


def _clamp(value: float, lo: float, hi: float) -> float:
    return float(min(hi, max(lo, value)))


class FlashGovernor:
    """Rate/intensity-limited strobe envelope driven by beat events."""

    __slots__ = (
        '_max_hz', '_max_brightness', '_flash_duration', '_beat_division',
        '_beat_threshold', '_min_interval', '_level', '_cooldown',
        '_was_high', '_beat_count',
    )

    def __init__(
        self,
        max_hz: float = 3.0,
        max_brightness: float = 0.5,
        flash_duration: float = 0.12,
        beat_division: int = 1,
        beat_threshold: float = 0.45,
    ) -> None:
        # Hard-clamp to the absolute safety ceilings.
        self._max_hz = _clamp(max_hz, 0.5, _ABS_MAX_HZ)
        self._max_brightness = _clamp(max_brightness, 0.0, _ABS_MAX_BRIGHTNESS)
        self._min_interval = 1.0 / self._max_hz
        # A flash must finish before the next is allowed, with headroom.
        self._flash_duration = _clamp(flash_duration, 0.02, 0.8 * self._min_interval)
        self._beat_division = max(1, int(beat_division))
        self._beat_threshold = _clamp(beat_threshold, 0.05, 1.0)

        self._level = 0.0
        self._cooldown = 0.0
        self._was_high = False
        self._beat_count = 0

    # ------------------------------------------------------------------ params
    @property
    def level(self) -> float:
        """Current flash brightness in ``[0, max_brightness]``."""
        return self._level

    @property
    def max_hz(self) -> float:
        return self._max_hz

    @property
    def max_brightness(self) -> float:
        return self._max_brightness

    @property
    def min_interval(self) -> float:
        return self._min_interval

    def set_max_brightness(self, value: float) -> float:
        """Set the brightness ceiling (re-clamped to the absolute cap)."""
        self._max_brightness = _clamp(value, 0.0, _ABS_MAX_BRIGHTNESS)
        self._level = min(self._level, self._max_brightness)
        return self._max_brightness

    def set_beat_division(self, value: int) -> int:
        self._beat_division = max(1, int(value))
        return self._beat_division

    # ------------------------------------------------------------------ update
    def update(self, dt: float, beat: float, *, active: bool = True) -> float:
        """Advance the envelope by ``dt`` given a ``beat`` signal in ``[0, 1]``.

        Returns the new :attr:`level`.  When ``active`` is False the envelope
        only decays (no new flashes are armed).  A flash is armed on a rising
        beat edge, subject to the division counter and the rate cooldown.
        """
        dt = max(0.0, float(dt))
        self._cooldown = max(0.0, self._cooldown - dt)

        high = float(beat) >= self._beat_threshold
        if active and high and not self._was_high:
            self._beat_count += 1
            if self._beat_count % self._beat_division == 0 and self._cooldown <= 0.0:
                self._level = self._max_brightness
                self._cooldown = self._min_interval
        self._was_high = high

        # Linear decay over the (clamped) flash duration.
        if self._level > 0.0:
            self._level = max(0.0, self._level - dt * (self._max_brightness / self._flash_duration))
        return self._level

    def reset(self) -> None:
        """Clear the envelope and beat state (e.g. when disabling)."""
        self._level = 0.0
        self._cooldown = 0.0
        self._was_high = False
        self._beat_count = 0
