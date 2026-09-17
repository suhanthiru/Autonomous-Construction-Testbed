"""Declared measurement windows for comparing records at different timesteps."""

from math import fsum, isfinite

from excavation_sim.actuation import ticks_per_update


def vertical_momentum_audit(
    velocities_m_s: list[float],
    actuator_forces_n: list[float],
    soil_impulses_n_s: list[float],
    *,
    mass_kg: float,
    dt_s: float,
    initial_velocity_m_s: float = 0.0,
    gravity_m_s2: float = 9.81,
) -> dict:
    """Compare current- and previous-step soil impulses against rigid momentum.

    The residual includes any unrecorded contacts or constraints. A small residual
    verifies this body's bookkeeping only, not soil momentum or physical accuracy.
    """
    count = len(velocities_m_s)
    if not count or len(actuator_forces_n) != count or len(soil_impulses_n_s) != count:
        raise ValueError("momentum channels must have equal nonzero length")
    values = [
        mass_kg,
        dt_s,
        initial_velocity_m_s,
        gravity_m_s2,
        *velocities_m_s,
        *actuator_forces_n,
        *soil_impulses_n_s,
    ]
    if not all(isfinite(value) for value in values) or mass_kg <= 0 or dt_s <= 0:
        raise ValueError("invalid momentum audit inputs")
    inferred = [
        mass_kg * (velocity - before) - (force - mass_kg * gravity_m_s2) * dt_s
        for velocity, before, force in zip(
            velocities_m_s,
            [initial_velocity_m_s] + velocities_m_s[:-1],
            actuator_forces_n,
            strict=True,
        )
    ]
    results = {}
    for name, impulses in (
        ("same_step", soil_impulses_n_s),
        ("one_step_lag", [0.0] + soil_impulses_n_s[:-1]),
    ):
        residuals = [a - b for a, b in zip(inferred, impulses, strict=True)]
        results[name] = {
            "max_abs_step_residual_n_s": max(abs(value) for value in residuals),
            "sum_abs_step_residual_n_s": fsum(abs(value) for value in residuals),
            "signed_total_residual_n_s": fsum(residuals),
        }
    results["inferred_contact_impulse_n_s"] = fsum(inferred)
    return results


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
