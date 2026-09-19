"""Isolate soil/contact timestep sensitivity under identical prescribed box motion."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM

from excavation_sim.actuation import ticks_per_update
from excavation_sim.analysis import windowed_force
from excavation_sim.provenance import environment_info, source_identity


def run(dt):
    steps = ticks_per_update(dt, 1.2)
    ticks_per_update(dt, 0.02)
    builder = newton.ModelBuilder()
    SolverImplicitMPM.register_custom_attributes(builder)
    body = builder.add_body(
        is_kinematic=True, xform=wp.transform(wp.vec3(0, 0, 0.35), wp.quat_identity())
    )
    builder.add_shape_box(
        body,
        hx=0.06,
        hy=0.06,
        hz=0.04,
        cfg=newton.ModelBuilder.ShapeConfig(density=0, mu=0.5),
    )
    builder.add_ground_plane()
    spacing = 0.02
    builder.add_particle_grid(
        pos=wp.vec3(-0.19, -0.19, 0.01),
        rot=wp.quat_identity(),
        vel=wp.vec3(0),
        dim_x=20,
        dim_y=20,
        dim_z=10,
        cell_x=spacing,
        cell_y=spacing,
        cell_z=spacing,
        mass=1600 * spacing**3,
        jitter=0,
        radius_mean=spacing / 2,
        custom_attributes={"mpm:friction": 0.6},
    )
    model = builder.finalize()
    cfg = SolverImplicitMPM.Config()
    cfg.voxel_size = 0.04
    cfg.grid_type = "fixed"
    cfg.grid_padding = 10
    cfg.max_active_cell_count = 1 << 15
    cfg.max_iterations = 100
    cfg.tolerance = 1e-5
    cfg.air_drag = 1.0
    cfg.strain_basis = "P0"
    cfg.critical_fraction = 0.0
    solver = SolverImplicitMPM(model, cfg)
    state, output = model.state(), model.state()
    solver.setup_collider(body_mass=wp.zeros_like(model.body_mass), body_q=state.body_q)
    trace = []
    for tick in range(steps):
        time = tick * dt
        z = 0.35 - 0.3 * min(time, 0.8) + 0.3 * max(time - 0.8, 0)
        velocity = -0.3 if time < 0.8 else 0.3
        state.body_q.assign(np.array([[0, 0, z, 0, 0, 0, 1]], dtype=np.float32))
        state.body_qd.assign(np.array([[0, 0, velocity, 0, 0, 0]], dtype=np.float32))
        solver.step(state, output, None, None, dt)
        state, output = output, state
        impulses, _, ids = solver.collect_collider_impulses(state)
        indices = ids.numpy()
        mapping = solver.collider_body_index.numpy()
        valid = (indices >= 0) & (indices < len(mapping))
        selected = np.zeros(len(indices), dtype=bool)
        selected[valid] = mapping[indices[valid]] == body
        impulse = impulses.numpy()[selected].sum(axis=0, dtype=np.float64)
        particles = state.particle_q.numpy()
        if not np.isfinite(impulse).all() or not np.isfinite(particles).all():
            raise RuntimeError(f"nonfinite state at tick {tick + 1}")
        trace.append(
            {
                "time_s": (tick + 1) * dt,
                "input_z_m": z,
                "input_vz_m_s": velocity,
                "impulse_n_s": impulse.tolist(),
            }
        )
    force = windowed_force([row["impulse_n_s"][2] for row in trace], dt, 0.02)
    return {
        "dt_s": dt,
        "duration_s": steps * dt,
        "boundary": "kinematic prescribed box, zero rotation; no actuator or proxy feedback",
        "mpm": {
            "iterations": 100,
            "tolerance": 1e-5,
            "voxel_m": 0.04,
            "spacing_m": spacing,
            "air_drag": 1.0,
            "friction": 0.6,
        },
        "peak_20ms_mean_n": max(force),
        "total_vertical_impulse_n_s": sum(row["impulse_n_s"][2] for row in trace),
        "min_particle_z_m": float(particles[:, 2].min()),
        "final_particle_positions_m": particles.tolist(),
        "trajectory": trace,
        "claim": "Numerical isolation diagnostic, not physical validation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dt", type=float, nargs="+", default=[0.005, 0.0025, 0.00125])
    args = parser.parse_args()
    if len(set(args.dt)) != len(args.dt):
        parser.error("timesteps must be distinct")
    for dt in args.dt:
        ticks_per_update(dt, 1.2)
        ticks_per_update(dt, 0.02)
    args.output.mkdir(parents=True, exist_ok=False)
    identity = source_identity(Path.cwd())
    wp.config.kernel_cache_dir = str(Path(".cache/warp").resolve())
    wp.init()
    results = []
    with wp.ScopedDevice("cuda:0"):
        for dt in args.dt:
            started = perf_counter()
            try:
                record = run(dt)
            except Exception as error:
                (args.output / "failure.json").write_text(
                    json.dumps(
                        {
                            "dt_s": dt,
                            "source": identity,
                            "error": f"{type(error).__name__}: {error}",
                            "completed_cases": results,
                        },
                        indent=2,
                    )
                )
                raise
            record.update(source=identity, environment=environment_info())
            record["source_changed"] = (
                identity["source_sha256"] != source_identity(Path.cwd())["source_sha256"]
            )
            record["wall_time_s"] = perf_counter() - started
            (args.output / f"dt-{dt}.json").write_text(json.dumps(record, indent=2))
            results.append(
                {
                    k: record[k]
                    for k in (
                        "dt_s",
                        "peak_20ms_mean_n",
                        "total_vertical_impulse_n_s",
                        "source_changed",
                    )
                }
            )
            (args.output / "summary.json").write_text(json.dumps(results, indent=2))
            print(results[-1], flush=True)
    return int(any(row["source_changed"] for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
