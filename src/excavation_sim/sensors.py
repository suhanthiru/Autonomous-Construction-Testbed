"""Sampled observations with explicit latency, freshness, and independent noise RNG."""

from collections import deque
from dataclasses import dataclass, replace
from math import isfinite

import numpy as np

from excavation_sim.core import Clock, Observation


@dataclass(frozen=True)
class SensorConfig:
    surface_enabled: bool = False
    sample_every_actions: int = 1
    latency_actions: int = 0
    position_noise_std_m: float = 0.0
    velocity_noise_std_m_s: float = 0.0
    force_noise_std_n: float = 0.0
    joint_position_noise_std_rad: float = 0.0
    joint_velocity_noise_std_rad_s: float = 0.0

    def __post_init__(self):
        if type(self.surface_enabled) is not bool:
            raise ValueError("surface_enabled must be boolean")
        if type(self.sample_every_actions) is not int or self.sample_every_actions < 1:
            raise ValueError("sample period must be a positive number of actions")
        if type(self.latency_actions) is not int or self.latency_actions < 0:
            raise ValueError("sensor latency must be a nonnegative number of actions")
        for value in (
            self.position_noise_std_m,
            self.velocity_noise_std_m_s,
            self.force_noise_std_n,
            self.joint_position_noise_std_rad,
            self.joint_velocity_noise_std_rad_s,
        ):
            if not isfinite(value) or value < 0:
                raise ValueError("noise scales must be finite and nonnegative")


class SensorStream:
    def __init__(self, config: SensorConfig, ticks_per_action: int, dt_s: float):
        Clock(dt_s, ticks_per_action)
        self.config, self.ticks_per_action, self.dt_s = config, ticks_per_action, dt_s

    def reset(self, seed):
        streams = np.random.SeedSequence([seed, 72591]).spawn(5)
        self.rngs = [np.random.default_rng(s) for s in streams]
        self.pending = deque()
        self.latest = None
        self.last_tick = -1

    def sample(self, raw: Observation) -> Observation:
        if raw.tick <= self.last_tick:
            raise ValueError("sensor time must advance")
        self.last_tick = raw.tick
        period = self.config.sample_every_actions * self.ticks_per_action
        if raw.tick % period == 0:
            changes = {}
            fields = [
                ("tool_position_m", self.config.position_noise_std_m),
                ("tool_velocity_m_s", self.config.velocity_noise_std_m_s),
                ("soil_force_n", self.config.force_noise_std_n),
                ("joint_position_rad", self.config.joint_position_noise_std_rad),
                ("joint_velocity_rad_s", self.config.joint_velocity_noise_std_rad_s),
            ]
            for rng, (name, std) in zip(self.rngs, fields, strict=True):
                values = getattr(raw, name)
                changes[name] = tuple(
                    float(v) for v in np.asarray(values) + rng.normal(0, std, len(values))
                )
            packet = replace(raw, **changes, sensor_capture_tick=raw.tick, sensor_valid=True)
            delivery = raw.tick + self.config.latency_actions * self.ticks_per_action
            self.pending.append((delivery, packet))
        while self.pending and self.pending[0][0] <= raw.tick:
            _, self.latest = self.pending.popleft()
        if self.latest is None:
            # No future sample leaks through the initial latency window.
            return Observation(
                tick=raw.tick,
                time_s=raw.time_s,
                tool_position_m=(0.0, 0.0, 0.0),
                tool_velocity_m_s=(0.0, 0.0, 0.0),
                soil_force_n=(0.0, 0.0, 0.0),
                joint_position_rad=(0.0,) * len(raw.joint_position_rad),
                joint_velocity_rad_s=(0.0,) * len(raw.joint_velocity_rad_s),
                sensor_capture_tick=None,
                sensor_age_s=0.0,
                sensor_valid=False,
            )
        return replace(
            self.latest,
            tick=raw.tick,
            time_s=raw.time_s,
            sensor_age_s=(raw.tick - self.latest.sensor_capture_tick) * self.dt_s,
        )


class ObservedWorld:
    """Policy-facing sensor wrapper; evaluator access to raw state is explicit."""

    def __init__(self, world, config: SensorConfig):
        self.world = world
        self.info, self.clock = world.info, world.clock
        self.stream = SensorStream(config, self.clock.substeps_per_action, self.clock.dt_s)

    def reset(self, seed):
        self.stream.reset(seed)
        self.raw = self.world.reset(seed)
        return self._sample()

    def step(self, command):
        self.raw = self.world.step(command)
        return self._sample()

    def _sample(self):
        raw = self.raw
        period = self.stream.config.sample_every_actions * self.clock.substeps_per_action
        if self.stream.config.surface_enabled and raw.tick % period == 0:
            if not hasattr(self.world, "capture_surface"):
                raise ValueError("backend does not support surface observations")
            raw = replace(raw, surface=self.world.capture_surface())
        return self.stream.sample(raw)

    def evaluation_observation(self):
        return self.raw

    def diagnostics(self):
        return self.world.diagnostics()

    def inspection_state(self):
        return self.world.inspection_state()

    def runtime_metadata(self):
        return self.world.runtime_metadata()

    def close(self):
        self.world.close()
