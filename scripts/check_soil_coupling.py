# SPDX-FileCopyrightText: Copyright (c) 2026 The Newton Developers
# SPDX-License-Identifier: Apache-2.0
# Adapted from Newton's rigid/MPM coupled-solver example; see THIRD_PARTY.md.
"""Small rigid/MPM feasibility fixture, not a physical validation benchmark.

Run explicitly with the physics extra installed. Outputs remain in runs/.
"""

import argparse
import json
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM, SolverXPBD
from newton.solvers.experimental.coupled import SolverCoupledProxy

from excavation_sim.actuation import ticks_per_update, vertical_servo_force
from excavation_sim.provenance import environment_info, source_identity


def run(
    steps: int,
    dt: float,
    with_soil: bool = True,
    drive: bool = False,
    control_dt: float | None = None,
    coupling_iterations: int = 1,
    hold: bool = False,
    mpm_iterations: int = 50,
    mpm_tolerance: float = 1e-4,
    voxel_size: float = 0.04,
    particle_spacing: float = 0.02,
    air_drag: float = 1.0,
    proxy_mode: str = "lagged",
) -> dict:
    if proxy_mode not in {"lagged", "staggered"}:
        raise ValueError("unsupported proxy transfer mode")
    if not np.isfinite(air_drag) or air_drag < 0:
        raise ValueError("air_drag must be finite and nonnegative")
    if type(mpm_iterations) is not int or mpm_iterations < 1:
        raise ValueError("mpm_iterations must be a positive integer")
    if not all(np.isfinite(v) and v > 0 for v in (mpm_tolerance, voxel_size, particle_spacing)):
        raise ValueError("MPM tolerance and spatial sizes must be finite and positive")
    dims = [ticks_per_update(particle_spacing, extent) for extent in (0.4, 0.4, 0.2)]
    if drive and hold:
        raise ValueError("choose either the driven trajectory or the stationary control")
    servo_enabled = drive or hold
    if type(coupling_iterations) is not int or coupling_iterations < 1:
        raise ValueError("coupling_iterations must be a positive integer")
    control_dt = dt if control_dt is None else control_dt
    control_ticks = ticks_per_update(dt, control_dt)
    identity = source_identity(Path.cwd())
    wp.config.kernel_cache_dir = str(Path(".cache/warp").resolve())
    wp.init()
    if not wp.get_device("cuda:0").is_cuda:
        raise RuntimeError("This fixture requires CUDA")
    with wp.ScopedDevice("cuda:0"):
        builder = newton.ModelBuilder()
        SolverImplicitMPM.register_custom_attributes(builder)
        body = builder.add_body(xform=wp.transform(wp.vec3(0, 0, 0.35), wp.quat_identity()))
        builder.add_shape_box(
            body,
            hx=0.06,
            hy=0.06,
            hz=0.04,
            cfg=newton.ModelBuilder.ShapeConfig(density=2000.0, mu=0.5),
        )
        builder.add_ground_plane()
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
            mass=1600 * spacing**3,
            jitter=0.0,
            radius_mean=spacing / 2,
            custom_attributes={"mpm:friction": 0.6},
        )
        model = builder.finalize()
        config = SolverImplicitMPM.Config()
        config.voxel_size = voxel_size
        config.grid_type = "fixed"
        config.grid_padding = 10
        config.max_active_cell_count = 1 << 15
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
                    solver=lambda view: SolverXPBD(view, iterations=10),
                    bodies=[body],
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
                        bodies=[body],
                        mass_scale=1.0,
                        mode=proxy_mode,
                        collision_pipeline=lambda _: None,
                    )
                ]
                if with_soil
                else [],
                iterations=coupling_iterations,
            ),
        )
        state = model.state()
        baseline_solver = SolverXPBD(model, iterations=10) if not with_soil else None
        baseline_output = model.state() if not with_soil else None
        control = model.control()
        pipeline = newton.CollisionPipeline(model, soft_contact_max=0)
        contacts = pipeline.contacts()
        trajectory = []
        mass = float(model.body_mass.numpy()[body])
        particle_masses = (
            model.particle_mass.numpy().astype(np.float64) if with_soil else np.empty(0)
        )
        actuator_force = 0.0
        target_velocity = 0.0
        for tick in range(steps):
            state.clear_forces()
            before_velocity = float(state.body_qd.numpy()[body, 2])
            if tick % control_ticks == 0:
                target_velocity = 0.0 if hold else (-0.3 if tick * dt < 0.8 else 0.3)
                actuator_force = (
                    vertical_servo_force(
                        target_velocity, before_velocity, gain=150.0, mass=mass, force_limit=60.0
                    )
                    if servo_enabled
                    else 0.0
                )
            force_buffer = np.zeros((model.body_count, 6), dtype=np.float32)
            force_buffer[body, 2] = actuator_force
            state.body_f.assign(force_buffer)
            pipeline.collide(state, contacts)
            if with_soil:
                solver.step(state, state, control, contacts, dt)
            else:
                # The proxy wrapper does not advance entries without an attached proxy.
                # Use the same rigid solver and four substeps for the empty-bed control.
                for _ in range(4):
                    state.clear_forces()
                    state.body_f.assign(force_buffer)
                    pipeline.collide(state, contacts)
                    baseline_solver.step(state, baseline_output, control, contacts, dt / 4)
                    state, baseline_output = baseline_output, state
            q = state.body_q.numpy()[body]
            particles = state.particle_q.numpy() if with_soil else np.empty((0, 3))
            velocities = state.body_qd.numpy()
            particle_velocities = state.particle_qd.numpy() if with_soil else np.empty((0, 3))
            soil_impulse = np.zeros(3)
            ground_impulse = np.zeros(3)
            unmapped_impulse = np.zeros(3)
            applied_contact_impulse_z = 0.0
            if with_soil:
                rigid_input_force = solver.entry_state("rigid", "input").body_f.numpy()
                applied_contact_impulse_z = (float(rigid_input_force[0, 2]) - actuator_force) * dt
                mpm = solver.solver("soil")
                impulses, _, collider_ids = mpm.collect_collider_impulses(
                    solver.entry_state("soil")
                )
                ids = collider_ids.numpy()
                mapping = mpm.collider_body_index.numpy()
                valid = (ids >= 0) & (ids < len(mapping))
                selected = np.zeros(len(ids), dtype=bool)
                selected[valid] = mapping[ids[valid]] >= 0
                # This fixture has exactly one dynamic body. Static ground is excluded.
                impulse_values = impulses.numpy().astype(np.float64)
                soil_impulse = impulse_values[selected].sum(axis=0)
                ground_selected = np.zeros(len(ids), dtype=bool)
                ground_selected[valid] = mapping[ids[valid]] == -1
                ground_impulse = impulse_values[ground_selected].sum(axis=0)
                unmapped_impulse = impulse_values[~(selected | ground_selected)].sum(axis=0)
            soil_momentum = (particle_masses[:, None] * particle_velocities).sum(axis=0)
            if not all(
                np.isfinite(a).all()
                for a in (q, particles, velocities, particle_velocities, soil_impulse)
            ):
                raise RuntimeError(f"Nonfinite state at tick {tick + 1}")
            trajectory.append(
                {
                    "tick": tick + 1,
                    "controller_updated": tick % control_ticks == 0,
                    "time_s": (tick + 1) * dt,
                    "body_z_m": float(q[2]),
                    "body_vz_m_s": float(velocities[body, 2]),
                    "requested_vz_m_s": target_velocity if servo_enabled else None,
                    "actuator_force_z_n": actuator_force,
                    "soil_impulse_n_s": soil_impulse.tolist(),
                    "impulse_on_ground_n_s": ground_impulse.tolist(),
                    "unmapped_collider_impulse_n_s": unmapped_impulse.tolist(),
                    "soil_momentum_kg_m_s": soil_momentum.tolist(),
                    "soil_mass_kg": float(particle_masses.sum()),
                    "mass_below_ground_tolerance_kg": float(
                        particle_masses[particles[:, 2] < -0.04].sum()
                    ),
                    "applied_contact_impulse_z_n_s": applied_contact_impulse_z,
                    "soil_force_z_n": float(soil_impulse[2] / dt),
                    "soil_min_z_m": float(particles[:, 2].min()) if with_soil else None,
                }
            )
        return {
            "purpose": "rigid/MPM coupling feasibility; not physical validation",
            "environment": environment_info(),
            "source": identity,
            "source_changed_during_run": identity["source_sha256"]
            != source_identity(Path.cwd())["source_sha256"],
            "initial_body_z_m": 0.35,
            "device": str(wp.get_device()),
            "dt_s": dt,
            "control_dt_s": control_dt,
            "rigid_substeps": 4,
            "coupling_iterations": coupling_iterations,
            "coupling_mode": proxy_mode,
            "numerics": {
                "mpm_iterations": mpm_iterations,
                "mpm_tolerance": mpm_tolerance,
                "voxel_size_m": voxel_size,
                "particle_spacing_m": spacing,
                "air_drag": air_drag,
                "proxy_mode": proxy_mode,
            },
            "with_soil": with_soil,
            "drive": drive,
            "hold": hold,
            "servo": {
                "gain_n_s_m": 150.0,
                "force_limit_n": 60.0,
                "velocity_m_s": 0.0 if hold else 0.3,
                "reverse_time_s": None if hold else 0.8,
            }
            if servo_enabled
            else None,
            "steps": steps,
            "particle_count": model.particle_count,
            "initial_soil_mass_kg": float(particle_masses.sum()),
            "initial_soil_momentum_kg_m_s": [0.0, 0.0, 0.0],
            "ground_tolerance_m": 0.04,
            "body_mass_kg": float(model.body_mass.numpy()[body]),
            "trajectory": trajectory,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--dt", type=float, default=0.005)
    parser.add_argument("--control-dt", type=float, help="servo period; defaults to physics dt")
    parser.add_argument("--coupling-iterations", type=int, default=1)
    parser.add_argument("--mpm-iterations", type=int, default=50)
    parser.add_argument("--mpm-tolerance", type=float, default=1e-4)
    parser.add_argument("--voxel-size", type=float, default=0.04)
    parser.add_argument("--particle-spacing", type=float, default=0.02)
    parser.add_argument("--air-drag", type=float, default=1.0)
    parser.add_argument("--proxy-mode", choices=["lagged", "staggered"], default="lagged")
    parser.add_argument("--without-soil", action="store_true")
    parser.add_argument("--drive", action="store_true", help="force-limited down/up velocity servo")
    parser.add_argument("--hold", action="store_true", help="stationary tool above settling soil")
    parser.add_argument("--output", type=Path, default=Path("runs/coupling-check.json"))
    args = parser.parse_args()
    if args.steps <= 0 or not np.isfinite(args.dt) or args.dt <= 0:
        parser.error("steps and dt must be positive and finite")
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    result = run(
        args.steps,
        args.dt,
        not args.without_soil,
        args.drive,
        args.control_dt,
        args.coupling_iterations,
        args.hold,
        args.mpm_iterations,
        args.mpm_tolerance,
        args.voxel_size,
        args.particle_spacing,
        args.air_drag,
        args.proxy_mode,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"Wrote {args.output}")
