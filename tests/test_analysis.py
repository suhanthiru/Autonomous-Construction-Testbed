import pytest

from excavation_sim.analysis import vertical_momentum_audit, windowed_force


def test_momentum_audit_detects_delayed_impulse_even_if_totals_match():
    result = vertical_momentum_audit(
        [0, 0.5, 0.5],
        [0, 0, 0],
        [1, 0, 0],
        mass_kg=2,
        dt_s=0.01,
        gravity_m_s2=0,
    )
    assert result["same_step"]["signed_total_residual_n_s"] == 0
    assert result["same_step"]["max_abs_step_residual_n_s"] == 1
    assert result["one_step_lag"]["max_abs_step_residual_n_s"] == 0


def test_momentum_audit_accounts_for_gravity_and_actuator():
    result = vertical_momentum_audit(
        [0.02],
        [4],
        [0],
        mass_kg=2,
        dt_s=0.01,
        gravity_m_s2=0,
    )
    assert result["same_step"]["max_abs_step_residual_n_s"] == pytest.approx(0)
    result = vertical_momentum_audit([-0.1], [0], [0], mass_kg=2, dt_s=0.01, gravity_m_s2=10)
    assert result["same_step"]["max_abs_step_residual_n_s"] == pytest.approx(0)


def test_measurement_windows_preserve_impulse_across_timesteps():
    coarse = windowed_force([0.1, 0.3, -0.2, 0.2], 0.01, 0.02)
    fine = windowed_force([0.05, 0.05, 0.15, 0.15, -0.1, -0.1, 0.1, 0.1], 0.005, 0.02)
    assert fine == pytest.approx(coarse)
    assert sum(coarse) * 0.02 == pytest.approx(0.4)


def test_incomplete_window_cannot_silently_discard_impulse():
    with pytest.raises(ValueError):
        windowed_force([1, 1, 100], 0.01, 0.02)
