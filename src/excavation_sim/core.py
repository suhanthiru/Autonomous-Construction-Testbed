"""Small, engine-independent contracts. All physical quantities use SI units."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol

from excavation_sim.surface import SurfacePacket


class Capability(StrEnum):
    GRANULAR_SOIL = "granular_soil"
    REACTION_WRENCH = "reaction_wrench"
    DYNAMIC_TOOL = "dynamic_tool"
    MOTION_REPLAY = "motion_replay"
    COMMAND_REPLAY = "command_replay"
    SHARED_TERRAIN = "shared_terrain"
    EXACT_RESTART = "exact_restart"


@dataclass(frozen=True)
class BackendInfo:
    name: str
    version: str
    capabilities: frozenset[Capability]
    limitations: tuple[str, ...]

    def require(self, requested: frozenset[Capability]) -> None:
        missing = requested - self.capabilities
        if missing:
            raise ValueError(f"{self.name} does not support: {', '.join(sorted(missing))}")


@dataclass(frozen=True)
class Clock:
    """Integer ticks prevent accumulated rounding errors at observation boundaries."""

    dt_s: float
    substeps_per_action: int

    def __post_init__(self) -> None:
        if not isfinite(self.dt_s) or self.dt_s <= 0:
            raise ValueError("dt_s must be finite and positive")
        if type(self.substeps_per_action) is not int or self.substeps_per_action < 1:
            raise ValueError("substeps_per_action must be a positive integer")

    def time_s(self, tick: int) -> float:
        if type(tick) is not int or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        return tick * self.dt_s


@dataclass(frozen=True)
class ToolCommand:
    """World-frame linear velocity request, interpreted by the backend's actuator."""

    velocity_m_s: tuple[float, float, float]

    def __post_init__(self) -> None:
        if len(self.velocity_m_s) != 3 or not all(isfinite(v) for v in self.velocity_m_s):
            raise ValueError("velocity_m_s must contain three finite values")


@dataclass(frozen=True)
class JointCommand:
    """Normalized slew, boom, stick, bucket velocity requests, each in [-1, 1]."""

    velocity_targets: tuple[float, float, float, float]

    def __post_init__(self):
        if len(self.velocity_targets) != 4 or not all(
            isfinite(v) and -1 <= v <= 1 for v in self.velocity_targets
        ):
            raise ValueError("four finite normalized joint commands are required")


@dataclass(frozen=True)
class Observation:
    """Declared ideal sensor packet; never contains hidden material parameters."""

    tick: int
    time_s: float
    tool_position_m: tuple[float, float, float]
    tool_velocity_m_s: tuple[float, float, float]
    soil_force_n: tuple[float, float, float]
    joint_position_rad: tuple[float, ...] = ()
    joint_velocity_rad_s: tuple[float, ...] = ()
    sensor_capture_tick: int | None = None
    sensor_age_s: float = 0.0
    sensor_valid: bool = True
    surface: SurfacePacket | None = None


@dataclass(frozen=True)
class Diagnostics:
    """Evaluator-only data, kept out of the policy call."""

    particle_mass_kg: float
    escaped_mass_kg: float
    finite: bool
    actuator_force_n: tuple[float, float, float]
    actuator_torque_nm: tuple[float, ...] = ()
    lifted_bucket_mass_kg: float | None = None
    deposited_mass_kg: float | None = None
    positive_actuator_work_j: float | None = None


class World(Protocol):
    info: BackendInfo
    clock: Clock

    def reset(self, seed: int) -> Observation: ...

    def step(self, command: ToolCommand | JointCommand) -> Observation: ...

    def diagnostics(self) -> Diagnostics: ...

    def close(self) -> None: ...


class Policy(Protocol):
    def reset(self, seed: int) -> None: ...

    def act(self, observation: Observation) -> ToolCommand | JointCommand: ...
