"""Preloaded open-bucket fixture: isolate collision geometry from digging control."""

import argparse
import json
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM

from excavation_sim.backends.newton_tool import NewtonToolWorld
from excavation_sim.provenance import source_identity
from excavation_sim.robots.excavator import add_bucket


def main(args):
    runtime = NewtonToolWorld()
    identity = source_identity(Path.cwd())
    with wp.ScopedDevice(runtime.device):
        builder = newton.ModelBuilder()
        SolverImplicitMPM.register_custom_attributes(builder)
        body = builder.add_body(
            is_kinematic=True, xform=wp.transform(wp.vec3(0, 0, 0.4), wp.quat_identity())
        )
        add_bucket(builder, body, newton.ModelBuilder.ShapeConfig(density=0, mu=0.5))
        builder.add_ground_plane()
        spacing = 0.01
        builder.add_particle_grid(
            pos=wp.vec3(0.025, -0.025, 0.375),
            rot=wp.quat_identity(),
            vel=wp.vec3(0),
            dim_x=8,
            dim_y=6,
            dim_z=5,
            cell_x=spacing,
            cell_y=spacing,
            cell_z=spacing,
            mass=1600 * spacing**3,
            radius_mean=spacing / 2,
            jitter=0.0,
            custom_attributes={"mpm:friction": 0.6},
        )
        model = builder.finalize()
        cfg = SolverImplicitMPM.Config()
        cfg.voxel_size = args.voxel
        cfg.grid_type = "fixed"
        cfg.grid_padding = 10
        cfg.max_active_cell_count = 1 << 16
        cfg.max_iterations = 100
        cfg.tolerance = 1e-5
        cfg.strain_basis = "P0"
        cfg.critical_fraction = 0.0
        solver = SolverImplicitMPM(model, cfg)
        state, out = model.state(), model.state()
        solver.setup_collider(body_mass=wp.zeros_like(model.body_mass), body_q=state.body_q)
        trace = []
        mass = model.particle_mass.numpy().astype(np.float64)
        for tick in range(400):
            solver.step(state, out, None, None, 0.0025)
            state, out = out, state
            if tick % 20 == 0 or tick == 399:
                q = state.particle_q.numpy()
                if not np.isfinite(q).all():
                    raise RuntimeError("nonfinite particles")
                inside = (
                    (q[:, 0] >= 0)
                    & (q[:, 0] <= 0.16)
                    & (abs(q[:, 1]) <= 0.06)
                    & (q[:, 2] >= 0.36)
                    & (q[:, 2] <= 0.46)
                )
                trace.append(
                    {
                        "time_s": (tick + 1) * 0.0025,
                        "inside_mass_kg": float(mass[inside].sum()),
                        "min_z_m": float(q[:, 2].min()),
                        "max_z_m": float(q[:, 2].max()),
                    }
                )
        args.output.mkdir(parents=True, exist_ok=False)
        np.save(args.output / "particles.npy", q)
        report = {
            "source": identity,
            "voxel_m": args.voxel,
            "dt_s": 0.0025,
            "initial_mass_kg": float(mass.sum()),
            "trace": trace,
            "scope": "preloaded static open bucket; not physical validation",
            "source_changed": identity["source_sha256"]
            != source_identity(Path.cwd())["source_sha256"],
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voxel", type=float, default=0.02)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
