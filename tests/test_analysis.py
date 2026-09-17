import pytest

from excavation_sim.analysis import windowed_force


def test_measurement_windows_preserve_impulse_across_timesteps():
    coarse = windowed_force([0.1, 0.3, -0.2, 0.2], 0.01, 0.02)
    fine = windowed_force([0.05, 0.05, 0.15, 0.15, -0.1, -0.1, 0.1, 0.1], 0.005, 0.02)
    assert fine == pytest.approx(coarse)
    assert sum(coarse) * 0.02 == pytest.approx(0.4)


def test_incomplete_window_cannot_silently_discard_impulse():
    with pytest.raises(ValueError):
        windowed_force([1, 1, 100], 0.01, 0.02)
