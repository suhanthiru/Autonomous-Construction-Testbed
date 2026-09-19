from dataclasses import replace

from test_rollout import FixtureWorld, Policy

from excavation_sim.evaluation import summarize_episode
from excavation_sim.rollout import rollout


def test_evaluator_uses_raw_force_and_retains_unsuccessful_budget(tmp_path):
    class World(FixtureWorld):
        def step(self, command):
            self.after = super().step(command)
            return replace(self.after, soil_force_n=(999, 0, 0))

        def evaluation_observation(self):
            return replace(self.after, soil_force_n=(12, 0, 0))

    directory = tmp_path / "episode"
    rollout(World(), Policy(), directory, seed=0, actions=3, config={}, source_root=tmp_path)
    report = summarize_episode(directory, load_limit_n=10)
    assert report["peak_load_n"] == 12
    assert report["time_over_load_limit_s"] > 0
    assert report["force_access"] == "raw"
    assert not report["task_success"]
