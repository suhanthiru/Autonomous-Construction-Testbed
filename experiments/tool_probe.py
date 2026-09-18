"""External scripted policy example: consumes only declared observations."""

from excavation_sim.core import Observation, ToolCommand


class ProbePolicy:
    def reset(self, seed: int) -> None:
        self.seed = seed

    def act(self, observation: Observation) -> ToolCommand:
        velocity = -0.15 if observation.time_s < 1.0 else 0.15
        if abs(observation.soil_force_n[2]) > 50:
            velocity = 0.15
        return ToolCommand((0.0, 0.0, velocity))
