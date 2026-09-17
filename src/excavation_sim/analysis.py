"""Declared measurement windows for comparing records at different timesteps."""

from math import fsum, isfinite

from excavation_sim.actuation import ticks_per_update


def windowed_force(impulses_n_s: list[float], dt_s: float, window_s: float) -> list[float]:
    """Nonoverlapping time-zero-aligned windows; never drop an incomplete tail."""
    width = ticks_per_update(dt_s, window_s)
    if not impulses_n_s or len(impulses_n_s) % width:
        raise ValueError("record must contain complete measurement windows")
    if not all(isfinite(value) for value in impulses_n_s):
        raise ValueError("impulses must be finite")
    return [
        fsum(impulses_n_s[start : start + width]) / window_s
        for start in range(0, len(impulses_n_s), width)
    ]
