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

from excavation_sim.provenance import environment_info, source_identity


def run(steps: int, dt: float, with_soil: bool = True) -> dict:
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
        spacing = 0.02
        builder.add_particle_grid(
            pos=wp.vec3(-0.19, -0.19, 0.01),
            rot=wp.quat_identity(),
            vel=wp.vec3(0),
            dim_x=20,
            dim_y=20,
            dim_z=10 if with_soil else 0,
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
        config.voxel_size = 0.04
        config.grid_type = "fixed"
        config.grid_padding = 10
        config.max_active_cell_count = 1 << 15
        config.max_iterations = 50
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
                        mode="lagged",
                        collision_pipeline=lambda _: None,
                    )
                ]
                if with_soil
                else [],
                iterations=1,
            ),
        )
        state = model.state()
        baseline_solver = SolverXPBD(model, iterations=10) if not with_soil else None
        baseline_output = model.state() if not with_soil else None
        control = model.control()
        pipeline = newton.CollisionPipeline(model, soft_contact_max=0)
        contacts = pipeline.contacts()
        trajectory = []
        for tick in range(steps):
            state.clear_forces()
            pipeline.collide(state, contacts)
            if with_soil:
                solver.step(state, state, control, contacts, dt)
            else:
                # The proxy wrapper does not advance entries without an attached proxy.
                # Use the same rigid solver and four substeps for the empty-bed control.
                for _ in range(4):
                    state.clear_forces()
                    pipeline.collide(state, contacts)
                    baseline_solver.step(state, baseline_output, control, contacts, dt / 4)
                    state, baseline_output = baseline_output, state
            q = state.body_q.numpy()[body]
            particles = state.particle_q.numpy() if with_soil else np.empty((0, 3))
            velocities = state.body_qd.numpy()
            particle_velocities = state.particle_qd.numpy() if with_soil else np.empty((0, 3))
            if not all(
                np.isfinite(a).all() for a in (q, particles, velocities, particle_velocities)
            ):
                raise RuntimeError(f"Nonfinite state at tick {tick + 1}")
            trajectory.append(
                {
                    "tick": tick + 1,
                    "time_s": (tick + 1) * dt,
                    "body_z_m": float(q[2]),
                    "soil_min_z_m": float(particles[:, 2].min()) if with_soil else None,
                }
            )
        return {
            "purpose": "rigid/MPM coupling feasibility; not physical validation",
            "environment": environment_info(),
            "source": source_identity(Path.cwd()),
            "device": str(wp.get_device()),
            "dt_s": dt,
            "with_soil": with_soil,
            "steps": steps,
            "particle_count": model.particle_count,
            "initial_soil_mass_kg": float(model.particle_mass.numpy().sum()) if with_soil else 0.0,
            "body_mass_kg": float(model.body_mass.numpy()[body]),
            "trajectory": trajectory,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--dt", type=float, default=0.005)
    parser.add_argument("--without-soil", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("runs/coupling-check.json"))
    args = parser.parse_args()
    if args.steps <= 0 or not np.isfinite(args.dt) or args.dt <= 0:
        parser.error("steps and dt must be positive and finite")
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    result = run(args.steps, args.dt, not args.without_soil)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"Wrote {args.output}")
