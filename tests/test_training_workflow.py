import importlib.util
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_rollout import FixtureWorld

from excavation_sim.core import JointCommand
from excavation_sim.packed import export_episode
from excavation_sim.rollout import rollout
from excavation_sim.scenarios import load_suite


def test_raw_and_packed_training_agree_and_heldout_data_is_rejected(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "reference_baseline", "experiments/behavior_cloning.py"
    )
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    suite_path = Path("scenarios/v1/suite.json")
    suite = load_suite(suite_path)

    class World(FixtureWorld):
        def observe(self):
            return replace(
                super().observe(),
                joint_position_rad=(0, 0, 0, 0),
                joint_velocity_rad_s=(0, 0, 0, 0),
            )

    class Policy:
        def reset(self, seed):
            pass

        def act(self, observation):
            return JointCommand((0.1, 0, 0, 0))

    config = {
        "scenario": suite["splits"]["train"][0],
        "split": "train",
        "suite_sha256": suite["sha256"],
    }
    raw, packed = tmp_path / "raw", tmp_path / "packed"
    world = World()
    rollout(world, Policy(), raw, seed=0, actions=4, config=config, source_root=tmp_path)
    export_episode(raw, packed, chunk_size=2)
    for source, output in [(raw, tmp_path / "raw-fit"), (packed, tmp_path / "packed-fit")]:
        baseline.train([source], output, 1.0, suite_path)
    a = baseline.ClonedPolicy(tmp_path / "raw-fit/policy.npz").act(world.observe())
    b = baseline.ClonedPolicy(tmp_path / "packed-fit/policy.npz").act(world.observe())
    np.testing.assert_allclose(a.velocity_targets, b.velocity_targets, atol=1e-12, rtol=0)
    heldout = tmp_path / "heldout"
    rollout(
        World(),
        Policy(),
        heldout,
        seed=0,
        actions=4,
        config={**config, "split": "test", "scenario": suite["splits"]["test"][0]},
        source_root=tmp_path,
    )
    with pytest.raises(ValueError, match="frozen training split"):
        baseline.train([heldout], tmp_path / "rejected-fit", 1.0, suite_path)
    with pytest.raises(ValueError, match="duplicate transition data"):
        baseline.train([raw, packed], tmp_path / "duplicate-fit", 1.0, suite_path)
