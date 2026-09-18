from dataclasses import replace

import pytest

from excavation_sim.core import Diagnostics, Observation
from excavation_sim.tasks import ExcavationTask, ExcavationTaskConfig


def test_task_requires_backend_material_measurements():
    task = ExcavationTask(ExcavationTaskConfig())
    o = Observation(1, 0.1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    d = Diagnostics(50.0, 0.0, True, (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="material accounting"):
        task.evaluate(o, d)


def test_deposit_reward_is_change_in_qualified_mass_not_repeated_payment():
    task = ExcavationTask(ExcavationTaskConfig(target_mass_kg=1.0))
    o = Observation(1, 0.1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    d = Diagnostics(50.0, 0.0, True, (0.0, 0.0, 0.0), deposited_mass_kg=0.4)
    assert task.evaluate(o, d).reward == 0.4
    assert task.evaluate(replace(o, tick=2, time_s=0.2), d).reward == 0
    result = task.evaluate(replace(o, tick=3, time_s=0.3), replace(d, deposited_mass_kg=1.0))
    assert result.success and result.terminated and not result.truncated
    with pytest.raises(RuntimeError):
        task.evaluate(replace(o, tick=4, time_s=0.4), d)


def test_timeout_is_not_success_and_reset_clears_task_state():
    task = ExcavationTask(ExcavationTaskConfig(time_limit_s=1.0))
    o = Observation(100, 1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    d = Diagnostics(50.0, 0.0, True, (0.0, 0.0, 0.0), deposited_mass_kg=0.0)
    result = task.evaluate(o, d)
    assert result.truncated and not result.terminated and not result.success
    task.reset()
    assert not task.evaluate(replace(o, tick=1, time_s=0.01), d).truncated
