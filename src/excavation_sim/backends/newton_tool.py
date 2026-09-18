# SPDX-FileCopyrightText: Copyright (c) 2026 The Newton Developers
# SPDX-License-Identifier: Apache-2.0
# Coupling setup adapted from Newton; see THIRD_PARTY.md.
"""Reusable experimental single-tool Newton world. No physical validation claim."""

import os
from dataclasses import dataclass, replace
from math import ceil, isfinite
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM, SolverXPBD
from newton.solvers.experimental.coupled import SolverCoupledProxy

from excavation_sim.actuation import ticks_per_update
from excavation_sim.core import (
    BackendInfo,
    Capability,
    Clock,
    Diagnostics,
    Observation,
    ToolCommand,
)


@dataclass(frozen=True)
class ToolWorldConfig:
    physics_dt_s: float = 0.0025
    action_dt_s: float = 0.02
    with_soil: bool = True
    voxel_size_m: float = 0.04
    particle_spacing_m: float = 0.02
    grid_margin_m: float = 0.5
    max_active_cells: int = 1 << 18
    mpm_iterations: int = 50
    mpm_tolerance: float = 1e-4
    coupling_iterations: int = 1
    air_drag: float = 1.0
    soil_friction: float = 0.6
    soil_density_kg_m3: float = 1600.0
    force_limit_n: float = 60.0
    servo_gain: float = 150.0
    velocity_limit_m_s: float = 0.3

    def __post_init__(self):
        if any(
            type(v) is not int or v < 1
            for v in (self.mpm_iterations, self.coupling_iterations, self.max_active_cells)
        ):
            raise ValueError("solver iteration counts must be positive integers")
        ticks_per_update(self.physics_dt_s, self.action_dt_s)
        for value in (
            self.voxel_size_m,
            self.mpm_tolerance,
            self.grid_margin_m,
            self.particle_spacing_m,
            self.force_limit_n,
            self.servo_gain,
            self.velocity_limit_m_s,
            self.soil_density_kg_m3,
        ):
            if not isfinite(value) or value <= 0:
                raise ValueError("world scales and actuator limits must be finite and positive")
        if not isfinite(self.soil_friction) or self.soil_friction < 0:
            raise ValueError("soil friction must be finite and nonnegative")
        if not isfinite(self.air_drag) or self.air_drag < 0:
            raise ValueError("air_drag must be finite and nonnegative")
        for extent in (0.4, 0.4, 0.2):
            ticks_per_update(self.particle_spacing_m, extent)


@wp.kernel
def audit_particles(
    q: wp.array(dtype=wp.vec3),
    v: wp.array(dtype=wp.vec3),
    mass: wp.array(dtype=float),
    result: wp.array(dtype=float),
    lower: wp.vec3,
    upper: wp.vec3,
):
    i = wp.tid()
    p = q[i]
    velocity = v[i]
    if (
        not wp.isfinite(p[0])
        or not wp.isfinite(p[1])
        or not wp.isfinite(p[2])
        or not wp.isfinite(velocity[0])
        or not wp.isfinite(velocity[1])
        or not wp.isfinite(velocity[2])
    ):
        wp.atomic_add(result, 1, 1.0)
    # Conservative fixed-grid support envelope; not a physical wall or deletion rule.
    if (
        p[0] < lower[0]
        or p[1] < lower[1]
        or p[2] < lower[2]
        or p[0] > upper[0]
        or p[1] > upper[1]
        or p[2] > upper[2]
    ):
        wp.atomic_add(result, 0, mass[i])


class NewtonToolWorld:
    info = BackendInfo(
        "newton-tool",
        "0.1",
        frozenset({Capability.GRANULAR_SOIL, Capability.REACTION_WRENCH, Capability.DYNAMIC_TOOL}),
        (
            "Experimental lagged coupling; force convergence unresolved",
            "One box tool, no excavator or bucket",
            "Ideal instantaneous sensors",
            "Reset reconstructs the world; exact restart unsupported",
        ),
    )

    def __init__(self, config: ToolWorldConfig | None = None):
        config = ToolWorldConfig() if config is None else config
        self.config = config
        if not config.with_soil:
            self.info = replace(
                self.info, capabilities=self.info.capabilities - {Capability.GRANULAR_SOIL}
            )
        self.clock = Clock(
            config.physics_dt_s, ticks_per_update(config.physics_dt_s, config.action_dt_s)
        )
        self._ready = False
        cache = str(Path(".w").resolve())
        wp.config.kernel_cache_dir = "\\\\?\\" + cache if os.name == "nt" else cache
        wp.init()
        self.device = wp.get_device("cuda:0")

    def reset(self, seed: int) -> Observation:
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        # The initial fixture is deterministic. The seed is recorded, not used as hidden noise.
        self.close()
        self.seed = seed
        with wp.ScopedDevice(self.device):
            self._build()
        self.tick = 0
        self._force = np.zeros(3)
        self._body_forces = np.zeros((self.model.body_count, 3))
        self._actuator = np.zeros(3)
        self._ready = True
        return self._observation()

    def _build(self):
        with_soil = self.config.with_soil
        voxel_size = self.config.voxel_size_m
        air_drag = self.config.air_drag
        mpm_iterations = self.config.mpm_iterations
        mpm_tolerance = self.config.mpm_tolerance
        coupling_iterations = self.config.coupling_iterations
        builder = newton.ModelBuilder()
        SolverImplicitMPM.register_custom_attributes(builder)
        bodies, joints, body = self._add_robot(builder)
        builder.add_ground_plane()
        self._add_soil(builder)
        model = builder.finalize()
        config = SolverImplicitMPM.Config()
        config.voxel_size = voxel_size
        config.grid_type = "fixed"
        config.grid_padding = ceil(self.config.grid_margin_m / voxel_size)
        config.max_active_cell_count = self.config.max_active_cells
        config.max_iterations = mpm_iterations
        config.tolerance = mpm_tolerance
        config.air_drag = air_drag
        config.strain_basis = "P0"
        config.critical_fraction = 0.0
        solver = SolverCoupledProxy(
            model=model,
            entries=[
                SolverCoupledProxy.Entry(
                    name="rigid",
                    solver=self._rigid_solver,
                    bodies=bodies,
                    joints=joints,
                    substeps=4,
                ),
                *(
                    [
                        SolverCoupledProxy.Entry(
                            name="soil",
                            solver=lambda view: SolverImplicitMPM(view, config),
                            particles=list(range(model.particle_count)),
                            in_place=True,
                        )
                    ]
                    if with_soil
                    else []
                ),
            ],
            coupling=SolverCoupledProxy.Config(
                proxies=[
                    SolverCoupledProxy.Proxy(
                        source="rigid",
                        destination="soil",
                        bodies=bodies,
                        mass_scale=1.0,
                        mode="lagged",
                        collision_pipeline=lambda _: None,
                    )
                ]
                if with_soil
                else [],
                iterations=coupling_iterations,
            ),
        )
        state = model.state()
        baseline_solver = self._rigid_solver(model) if not with_soil else None
        baseline_output = model.state() if not with_soil else None
        control = model.control()
        pipeline = newton.CollisionPipeline(model, soft_contact_max=0)
        contacts = pipeline.contacts()
        self.model, self.solver, self.state = model, solver, state
        self.body, self.control = body, control
        self.pipeline, self.contacts = pipeline, contacts
        self.baseline_solver, self.baseline_output = baseline_solver, baseline_output
        self.mass = float(model.body_mass.numpy()[body])
        self.soil_mass = float(model.particle_mass.numpy().astype(np.float64).sum())
        self._audit = wp.zeros(2, dtype=float)
        lower, upper = np.array([-1.0, -1.0, -0.04]), np.array([1.0, 1.0, 1.0])
        if model.particle_count:
            initial = model.particle_q.numpy()
            margin = (config.grid_padding - 2) * config.voxel_size
            lower = np.maximum(lower, initial.min(axis=0) - margin)
            upper = np.minimum(upper, initial.max(axis=0) + margin)
        self._audit_lower, self._audit_upper = wp.vec3(*lower), wp.vec3(*upper)
        self._initialize_state()

    def _add_soil(self, builder):
        particle_spacing = self.config.particle_spacing_m
        dims = [ticks_per_update(particle_spacing, extent) for extent in (0.4, 0.4, 0.2)]
        with_soil = self.config.with_soil
        spacing = particle_spacing
        builder.add_particle_grid(
            pos=wp.vec3(-0.2 + spacing / 2, -0.2 + spacing / 2, spacing / 2),
            rot=wp.quat_identity(),
            vel=wp.vec3(0),
            dim_x=dims[0],
            dim_y=dims[1],
            dim_z=dims[2] if with_soil else 0,
            cell_x=spacing,
            cell_y=spacing,
            cell_z=spacing,
            mass=self.config.soil_density_kg_m3 * spacing**3,
            jitter=0.0,
            radius_mean=spacing / 2,
            custom_attributes={"mpm:friction": self.config.soil_friction},
        )

    def _rigid_solver(self, model):
        return SolverXPBD(model, iterations=10)

    def _add_robot(self, builder):
        body = builder.add_body(xform=wp.transform(wp.vec3(0, 0, 0.35), wp.quat_identity()))
        builder.add_shape_box(
            body,
            hx=0.06,
            hy=0.06,
            hz=0.04,
            cfg=newton.ModelBuilder.ShapeConfig(density=2000.0, mu=0.5),
        )
        return [body], [], body

    def _initialize_state(self):
        pass

    def _require_ready(self):
        if not self._ready:
            raise RuntimeError("reset the world before use; closed worlds require reset")

    def _observation(self):
        self._require_ready()
        q = self.state.body_q.numpy()[self.body, :3]
        v = self.state.body_qd.numpy()[self.body, :3]
        if not np.isfinite(q).all() or not np.isfinite(v).all():
            raise RuntimeError("nonfinite tool state")
        return Observation(
            self.tick,
            self.clock.time_s(self.tick),
            tuple(map(float, q)),
            tuple(map(float, v)),
            tuple(map(float, self._force)),
        )

    def _command_forces(self, command):
        target = np.clip(
            command.velocity_m_s, -self.config.velocity_limit_m_s, self.config.velocity_limit_m_s
        )
        velocity = self.state.body_qd.numpy()[self.body, :3]
        force = self.config.servo_gain * (target - velocity)
        force[2] += self.mass * 9.81
        force *= min(1.0, self.config.force_limit_n / max(float(np.linalg.norm(force)), 1e-12))
        self._actuator = force.copy()
        buffer = np.zeros((self.model.body_count, 6), dtype=np.float32)
        buffer[self.body, :3] = force
        return buffer

    def _substep_forces(self, command, buffer):
        return buffer

    def step(self, command: ToolCommand) -> Observation:
        self._require_ready()
        dt = self.clock.dt_s
        total_impulse = np.zeros((self.model.body_count, 3))
        with wp.ScopedDevice(self.device):
            buffer = self._command_forces(command)
            for _ in range(self.clock.substeps_per_action):
                buffer = self._substep_forces(command, buffer)
                self.state.clear_forces()
                self.state.body_f.assign(buffer)
                self.pipeline.collide(self.state, self.contacts)
                if self.config.with_soil:
                    self.solver.step(self.state, self.state, self.control, self.contacts, dt)
                    mpm = self.solver.solver("soil")
                    impulse, _, ids = mpm.collect_collider_impulses(self.solver.entry_state("soil"))
                    ids, mapping = ids.numpy(), mpm.collider_body_index.numpy()
                    valid = (ids >= 0) & (ids < len(mapping))
                    body_ids = np.full(len(ids), -1, dtype=int)
                    body_ids[valid] = mapping[ids[valid]]
                    impulses = impulse.numpy()
                    for body in range(self.model.body_count):
                        total_impulse[body] += impulses[body_ids == body].sum(
                            axis=0, dtype=np.float64
                        )
                else:
                    for _ in range(4):
                        self.state.clear_forces()
                        self.state.body_f.assign(buffer)
                        self.pipeline.collide(self.state, self.contacts)
                        self.baseline_solver.step(
                            self.state, self.baseline_output, self.control, self.contacts, dt / 4
                        )
                        self.state, self.baseline_output = self.baseline_output, self.state
                self.tick += 1
            self._body_forces = total_impulse / self.config.action_dt_s
            self._force = self._body_forces[self.body].copy()
            diagnostics = self.diagnostics()
            if not diagnostics.finite:
                raise RuntimeError(f"nonfinite soil at tick {self.tick}")
        return self._observation()

    def diagnostics(self) -> Diagnostics:
        self._require_ready()
        with wp.ScopedDevice(self.device):
            self._audit.zero_()
            if self.model.particle_count:
                wp.launch(
                    audit_particles,
                    dim=self.model.particle_count,
                    inputs=[
                        self.state.particle_q,
                        self.state.particle_qd,
                        self.model.particle_mass,
                        self._audit,
                        self._audit_lower,
                        self._audit_upper,
                    ],
                )
            audit = self._audit.numpy()
        finite = bool(
            audit[1] == 0
            and np.isfinite(self.state.body_q.numpy()).all()
            and np.isfinite(self.state.body_qd.numpy()).all()
            and np.isfinite(self._force).all()
        )
        return Diagnostics(
            self.soil_mass, float(audit[0]), finite, tuple(map(float, self._actuator))
        )

    def inspection_state(self) -> dict:
        """Explicit privileged host copy for rendering; never included in policy observations."""
        self._require_ready()
        return {
            "tick": self.tick,
            "shapes": [
                {"body": int(body), "pose": pose.tolist(), "half": scale.tolist()}
                for body, pose, scale, kind in zip(
                    self.model.shape_body.numpy(),
                    self.model.shape_transform.numpy(),
                    self.model.shape_scale.numpy(),
                    self.model.shape_type.numpy(),
                    strict=True,
                )
                if kind == int(newton.GeoType.BOX)
            ],
            "body_poses": self.state.body_q.numpy().copy(),
            "particles": (
                self.state.particle_q.numpy().copy()
                if self.model.particle_count
                else np.empty((0, 3), dtype=np.float32)
            ),
        }

    def close(self):
        self._ready = False
        for name in (
            "model",
            "solver",
            "state",
            "control",
            "pipeline",
            "contacts",
            "baseline_solver",
            "baseline_output",
            "_audit",
            "_material_metrics",
            "_lift_dwell",
            "_ever_lifted",
        ):
            if hasattr(self, name):
                delattr(self, name)
