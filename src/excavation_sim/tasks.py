"""Task goals and rewards are evaluated outside the world integrator."""

from dataclasses import dataclass
from math import isfinite

from excavation_sim.core import Diagnostics, Observation


@dataclass(frozen=True)
class TaskResult:
    reward: float
    success: bool
    terminated: bool
    truncated: bool
    metrics: dict


@dataclass(frozen=True)
class ExcavationTaskConfig:
    kind: str = "deposit"
    target_mass_kg: float = 0.5
    contact_force_n: float = 10.0
    time_limit_s: float = 12.0

    def __post_init__(self):
        if self.kind not in {"probe", "scoop", "deposit"}:
            raise ValueError("unknown task")
        if not all(
            isfinite(v) and v > 0
            for v in (self.target_mass_kg, self.contact_force_n, self.time_limit_s)
        ):
            raise ValueError("task targets must be finite and positive")


class ExcavationTask:
    def __init__(self, config: ExcavationTaskConfig):
        self.config = config
        self.reset()

    def reset(self):
        self.previous_score = 0.0
        self.last_tick = -1
        self.finished = False

    def evaluate(self, observation: Observation, diagnostics: Diagnostics) -> TaskResult:
        if self.finished or observation.tick <= self.last_tick:
            raise RuntimeError("task transitions must advance time; reset finished tasks")
        if not diagnostics.finite:
            raise ValueError("nonfinite simulation cannot earn task reward")
        if self.config.kind == "probe":
            score = sum(v * v for v in observation.soil_force_n) ** 0.5
            target = self.config.contact_force_n
        else:
            score = (
                diagnostics.lifted_bucket_mass_kg
                if self.config.kind == "scoop"
                else diagnostics.deposited_mass_kg
            )
            if score is None:
                raise ValueError("backend does not provide required material accounting")
            target = self.config.target_mass_kg
        if not isfinite(score) or score < 0:
            raise ValueError("invalid task score")
        success = score >= target
        truncated = observation.time_s >= self.config.time_limit_s and not success
        reward = score - self.previous_score
        self.previous_score = score
        self.last_tick = observation.tick
        self.finished = success or truncated
        return TaskResult(
            reward,
            success,
            success,
            truncated,
            {
                "score": score,
                "target": target,
                "time_s": observation.time_s,
                "positive_actuator_work_j": diagnostics.positive_actuator_work_j,
                "escaped_mass_kg": diagnostics.escaped_mass_kg,
            },
        )
