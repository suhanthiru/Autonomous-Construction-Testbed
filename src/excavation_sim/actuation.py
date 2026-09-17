"""Engine-independent, force-limited velocity servo in SI units."""

from math import isclose, isfinite


def ticks_per_update(physics_dt_s: float, control_dt_s: float) -> int:
    """Require aligned integer clocks rather than rounding a requested control rate."""
    if not all(isfinite(v) and v > 0 for v in (physics_dt_s, control_dt_s)):
        raise ValueError("clock periods must be finite and positive")
    ratio = control_dt_s / physics_dt_s
    ticks = round(ratio)
    if ticks < 1 or not isclose(ratio, ticks, rel_tol=0, abs_tol=1e-9):
        raise ValueError("control period must be an integer multiple of the physics timestep")
    return ticks


def vertical_servo_force(
    requested_velocity: float,
    measured_velocity: float,
    *,
    gain: float,
    mass: float,
    force_limit: float,
    gravity: float = 9.81,
) -> float:
    """Saturate total actuator force, including gravity compensation (positive z up)."""
    values = (requested_velocity, measured_velocity, gain, mass, force_limit, gravity)
    if not all(isfinite(value) for value in values):
        raise ValueError("servo inputs must be finite")
    if gain < 0 or mass <= 0 or force_limit <= 0 or gravity < 0:
        raise ValueError("invalid gain, mass, force limit, or gravity")
    force = gain * (requested_velocity - measured_velocity) + mass * gravity
    return max(-force_limit, min(force_limit, force))
