import pytest

from excavation_sim.actuation import vertical_servo_force


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
