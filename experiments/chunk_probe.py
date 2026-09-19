"""External three-action tool chunks; no simulator source changes are needed."""

from excavation_sim.chunks import ChunkExecutor
from excavation_sim.core import ToolCommand


class Planner:
    def reset(self, seed):
        self.seed = seed

    def plan(self, observation):
        velocity = -0.1 if observation.time_s < 1.5 else 0.1
        return [ToolCommand((0, 0, velocity)) for _ in range(3)]


class ProbePolicy(ChunkExecutor):
    def __init__(self):
        super().__init__(Planner(), ToolCommand((0, 0, 0)))
