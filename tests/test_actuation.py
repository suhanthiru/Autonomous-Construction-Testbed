import pytest

from excavation_sim.actuation import ticks_per_update, vertical_servo_force


def test_control_clock_preserves_requested_period():
    for dt in (0.005, 0.0025, 0.00125):
        ticks = ticks_per_update(dt, 0.005)
        assert [i * dt for i in range(0, 16 * ticks, ticks)] == [i * 0.005 for i in range(16)]


@pytest.mark.parametrize("dt,period", [(0.003, 0.005), (0.01, 0.005), (0, 0.005)])
def test_unaligned_control_clock_is_rejected(dt, period):
    with pytest.raises(ValueError):
        ticks_per_update(dt, period)


def test_gravity_compensation_is_inside_force_budget():
    assert vertical_servo_force(0, 0, gain=100, mass=10, force_limit=20) == 20


def test_servo_has_correct_direction_and_equilibrium():
    assert vertical_servo_force(0, 0, gain=100, mass=2, force_limit=100) == 19.62
    assert vertical_servo_force(-1, 0, gain=100, mass=2, force_limit=30) == -30
    assert vertical_servo_force(1, 0, gain=100, mass=2, force_limit=30) == 30


@pytest.mark.parametrize("velocity", [float("nan"), float("inf")])
def test_nonfinite_commands_fail(velocity):
    with pytest.raises(ValueError):
        vertical_servo_force(velocity, 0, gain=100, mass=2, force_limit=30)
