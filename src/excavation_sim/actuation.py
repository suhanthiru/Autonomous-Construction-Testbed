"""Engine-independent, force-limited velocity servo in SI units."""

from math import isfinite


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
