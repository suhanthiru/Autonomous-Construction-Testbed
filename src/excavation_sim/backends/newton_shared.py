"""Two dynamic box tools sharing one coupled soil domain and one simulation clock."""

from collections.abc import Mapping

import newton
import numpy as np
import warp as wp

from excavation_sim.backends.newton_tool import NewtonToolWorld
from excavation_sim.core import BackendInfo, Capability, Observation, ToolCommand


class NewtonSharedToolWorld(NewtonToolWorld):
    agent_ids = ("tool_0", "tool_1")
    info = BackendInfo(
        "newton-shared-tools", "0.1",
        frozenset({Capability.GRANULAR_SOIL, Capability.REACTION_WRENCH,
                   Capability.DYNAMIC_TOOL, Capability.SHARED_TERRAIN}),
        ("Two box tools; no fleet or articulated-machine claim",
         "Experimental lagged coupling; force convergence unresolved",
         "Ideal observations; whole-world reset only"),
    )

    def _add_robot(self, builder):
        bodies = []
        for name, x in zip(self.agent_ids, (-0.09, 0.09), strict=True):
            body = builder.add_body(xform=wp.transform(wp.vec3(x, 0, 0.30), wp.quat_identity()),
                                    label=name)
            builder.add_shape_box(body, hx=0.04, hy=0.06, hz=0.04,
                                  cfg=newton.ModelBuilder.ShapeConfig(density=1200.0))
            bodies.append(body)
        self.agent_bodies = dict(zip(self.agent_ids, bodies, strict=True))
        return bodies, [], bodies[0]

    def reset_agents(self, seed: int) -> dict[str, Observation]:
        super().reset(seed)
        self._agent_actuators = np.zeros((self.model.body_count, 3))
        return self.observations()

    def observations(self) -> dict[str, Observation]:
        self._require_ready()
        poses, velocities = self.state.body_q.numpy(), self.state.body_qd.numpy()
        return {
            name: Observation(self.tick, self.clock.time_s(self.tick),
                              tuple(map(float, poses[body, :3])),
                              tuple(map(float, velocities[body, :3])),
                              tuple(map(float, self._body_forces[body])))
            for name, body in self.agent_bodies.items()
        }

    def _command_forces(self, commands):
        if not isinstance(commands, Mapping) or set(commands) != set(self.agent_ids):
            raise ValueError("submit exactly one command for each declared agent")
        if not all(isinstance(commands[name], ToolCommand) for name in self.agent_ids):
            raise TypeError("shared tools require ToolCommand values")
        velocities = self.state.body_qd.numpy()
        masses = self.model.body_mass.numpy()
        buffer = np.zeros((self.model.body_count, 6), dtype=np.float32)
        for name in self.agent_ids:
            body = self.agent_bodies[name]
            target = np.clip(commands[name].velocity_m_s,
                             -self.config.velocity_limit_m_s, self.config.velocity_limit_m_s)
            force = self.config.servo_gain * (target - velocities[body, :3])
            force[2] += masses[body] * 9.81
            force *= min(1.0, self.config.force_limit_n /
                         max(float(np.linalg.norm(force)), 1e-12))
            buffer[body, :3] = force
        self._agent_actuators = buffer[:, :3].copy()
        self._actuator = self._agent_actuators[self.body]
        return buffer

    def step_agents(self, commands: Mapping[str, ToolCommand]) -> dict[str, Observation]:
        super().step(commands)
        return self.observations()

    def _substep_forces(self, commands, buffer):
        # The lightweight tools need damping at the physics rate. Holding a stiff
        # velocity servo's force for an entire action interval amplifies contact noise.
        return self._command_forces(commands)

    def agent_loads(self) -> dict[str, dict]:
        self._require_ready()
        return {name: {"actuator_force_n": self._agent_actuators[body].tolist(),
                       "soil_force_n": self._body_forces[body].tolist()}
                for name, body in self.agent_bodies.items()}
