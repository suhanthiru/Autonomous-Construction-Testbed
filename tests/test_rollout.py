import json

import pytest

from excavation_sim.core import BackendInfo, Clock, Diagnostics, Observation, ToolCommand
from excavation_sim.recording import read_transitions
from excavation_sim.rollout import rollout


class FixtureWorld:
    info = BackendInfo("cpu-contract-fixture", "1", frozenset(), ("No soil physics",))
    clock = Clock(0.01, 2)

    def reset(self, seed):
        self.tick = 0
        self.closed = False
        return self.observe()

    def observe(self):
        return Observation(
            self.tick,
            self.clock.time_s(self.tick),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        )

    def step(self, command):
        self.tick += 2
        return self.observe()

    def diagnostics(self):
        return Diagnostics(123.456, 0.0, True, (0.0, 0.0, 0.0))

    def close(self):
        self.closed = True


class Policy:
    def reset(self, seed):
        pass

    def act(self, observation):
        assert not hasattr(observation, "particle_mass_kg")
        return ToolCommand((0.0, 0.0, 0.0))


def test_rollout_records_budget_and_separates_privileged_data(tmp_path):
    world = FixtureWorld()
    output = tmp_path / "episode"
    report = rollout(world, Policy(), output, seed=3, actions=4, config={}, source_root=tmp_path)
    rows = read_transitions(output)
    assert len(rows) == 4
    assert report["simulated_time_s"] == 0.08
    assert world.closed
    assert "123.456" not in (output / "transitions.jsonl").read_text()
    assert "123.456" in (output / "evaluation.jsonl").read_text()
    assert json.loads((output / "outcome.json").read_text())["status"] == "completed"
    assessment = json.loads((output / "manifest.json").read_text())["validation_snapshot"]
    assert not assessment["validation_complete"]
    assert assessment["errors"]  # Fixture has no admitted physical evidence.


def test_policy_failure_is_retained_and_world_closed(tmp_path):
    class BrokenPolicy(Policy):
        def act(self, observation):
            raise RuntimeError("policy failed")

    world = FixtureWorld()
    output = tmp_path / "episode"
    with pytest.raises(RuntimeError, match="policy failed"):
        rollout(world, BrokenPolicy(), output, seed=0, actions=4, config={}, source_root=tmp_path)
    assert world.closed
    assert json.loads((output / "outcome.json").read_text())["status"] == "failed"
