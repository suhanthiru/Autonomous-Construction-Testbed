"""Compile declared scenario preparation into the articulated Newton backend."""

from dataclasses import replace

import newton
import warp as wp

from excavation_sim.backends.newton_excavator import NewtonExcavatorWorld
from excavation_sim.backends.newton_tool import ToolWorldConfig
from excavation_sim.core import Capability
from excavation_sim.scenarios import Scenario, particle_positions


class NewtonScenarioWorld(NewtonExcavatorWorld):
    def __init__(self, scenario: Scenario, config: ToolWorldConfig | None = None):
        self.scenario = scenario
        super().__init__(
            replace(
                config or ToolWorldConfig(),
                soil_friction=scenario.friction,
                soil_density_kg_m3=scenario.density_kg_m3,
            )
        )
        capabilities = self.info.capabilities
        if scenario.obstacle == "dynamic":
            capabilities |= {Capability.DYNAMIC_OBSTACLE}
        elif scenario.obstacle == "anchored":
            capabilities |= {Capability.ANCHORED_OBSTACLE}
        self.info = replace(
            self.info, name="newton-scenario-excavator", capabilities=frozenset(capabilities)
        )

    def reset(self, seed):
        if seed != self.scenario.seed:
            raise ValueError("reset seed must match the resolved scenario seed")
        return super().reset(seed)

    def _add_robot(self, builder):
        bodies, joints, primary = super()._add_robot(builder)
        self.obstacle_body = None
        if self.scenario.obstacle != "none":
            pose = wp.transform(wp.vec3(-0.02, 0, 0.10), wp.quat_identity())
            joint = builder.joint_count
            if self.scenario.obstacle == "dynamic":
                obstacle = builder.add_body(xform=pose, label="buried_rigid_obstacle")
            else:
                obstacle = builder.add_link(xform=pose, label="anchored_rigid_obstacle")
                builder.add_joint_fixed(-1, obstacle, parent_xform=pose)
                builder.add_articulation([joint], label="anchored_obstacle")
            builder.add_shape_box(
                obstacle,
                hx=0.04,
                hy=0.04,
                hz=0.04,
                cfg=newton.ModelBuilder.ShapeConfig(density=2600, mu=0.6),
            )
            bodies.append(obstacle)
            joints.append(joint)
            self.obstacle_body = obstacle
        return bodies, joints, primary

    def _add_soil(self, builder):
        if not self.config.with_soil:
            return
        spacing = self.config.particle_spacing_m
        points = particle_positions(self.scenario, spacing)
        builder.add_particles(
            pos=points,
            vel=[(0, 0, 0)] * len(points),
            mass=[self.config.soil_density_kg_m3 * spacing**3] * len(points),
            radius=[spacing / 2] * len(points),
            custom_attributes={"mpm:friction": [self.scenario.friction] * len(points)},
        )
