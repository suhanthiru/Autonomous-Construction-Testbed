"""Exploratory square-rod penetration at published laboratory scale.

Plane facets approximate the cylindrical chamber. No calibration or physical pass
is implied by completing this fixture; preparation and force uncertainty remain open.
"""

import argparse
import json
import math
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM

from excavation_sim.datasets import file_hash, rheometer_volume_fraction
from excavation_sim.provenance import environment_info, source_identity


def run(args):
    if args.phi not in (0.57, 0.59) or not all(
        math.isfinite(v) and v > 0 for v in (args.dt, args.spacing, args.voxel, args.depth)
    ):
        raise ValueError("invalid packing condition or numerical settings")
    if args.depth > 0.08:
        raise ValueError("depth exceeds the published apparatus range")
    if not all(math.isfinite(v) and v >= 0 for v in (args.friction, args.tool_friction)):
        raise ValueError("friction must be finite and nonnegative")
    identity = source_identity(Path.cwd())
    reference = rheometer_volume_fraction(args.data)
    condition = next(c for c in reference["conditions"] if c["packing_fraction"] == args.phi)
    wp.config.kernel_cache_dir = str(Path(".cache/warp").resolve())
    wp.init()
    with wp.ScopedDevice("cuda:0"):
        builder = newton.ModelBuilder()
        SolverImplicitMPM.register_custom_attributes(builder)
        rod = builder.add_body(
            is_kinematic=True, xform=wp.transform(wp.vec3(0, 0, 0.342), wp.quat_identity())
        )
        builder.add_shape_box(
            rod,
            hx=0.00635,
            hy=0.00635,
            hz=0.075,
            cfg=newton.ModelBuilder.ShapeConfig(density=0, mu=args.tool_friction),
        )
        builder.add_ground_plane(cfg=newton.ModelBuilder.ShapeConfig(mu=0.5))
        for i in range(32):
            theta = 2 * math.pi * i / 32
            builder.add_shape_plane(
                plane=(-math.cos(theta), -math.sin(theta), 0.0, 0.108),
                width=0,
                length=0,
                cfg=newton.ModelBuilder.ShapeConfig(mu=0.5),
            )
        count_xy = math.ceil(0.216 / args.spacing)
        count_z = math.ceil(0.267 / args.spacing)
        dx, dz = 0.216 / count_xy, 0.267 / count_z
        x = -0.108 + (np.arange(count_xy) + 0.5) * dx
        z = (np.arange(count_z) + 0.5) * dz
        points = np.stack(np.meshgrid(x, x, z, indexing="ij"), axis=-1).reshape(-1, 3)
        points = points[(points[:, :2] ** 2).sum(axis=1) < 0.108**2].astype(np.float32)
        n = len(points)
        particle_mass = 2500 * args.phi * dx * dx * dz
        builder.add_particles(
            pos=points.tolist(),
            vel=np.zeros_like(points).tolist(),
            mass=[particle_mass] * n,
            radius=[min(dx, dz) / 2] * n,
            custom_attributes={"mpm:friction": [args.friction] * n},
        )
        model = builder.finalize()
        cfg = SolverImplicitMPM.Config()
        cfg.voxel_size = args.voxel
        cfg.grid_type = "fixed"
        cfg.grid_padding = 8
        cfg.max_active_cell_count = 1 << 19
        cfg.max_iterations = 100
        cfg.tolerance = 1e-5
        cfg.strain_basis = "P0"
        cfg.critical_fraction = 0.0
        cfg.air_drag = 1.0
        solver = SolverImplicitMPM(model, cfg)
        state, output = model.state(), model.state()
        solver.setup_collider(body_mass=wp.zeros_like(model.body_mass), body_q=state.body_q)
        speed = 0.01
        steps = math.ceil(args.depth / (speed * args.dt))
        trace = []
        for tick in range(steps):
            depth = tick * speed * args.dt
            state.body_q.assign(np.array([[0, 0, 0.342 - depth, 0, 0, 0, 1]], dtype=np.float32))
            state.body_qd.assign(np.array([[0, 0, -speed, 0, 0, 0]], dtype=np.float32))
            solver.step(state, output, None, None, args.dt)
            state, output = output, state
            impulses, _, ids = solver.collect_collider_impulses(state)
            indices = ids.numpy()
            mapping = solver.collider_body_index.numpy()
            valid = (indices >= 0) & (indices < len(mapping))
            mask = np.zeros(len(indices), dtype=bool)
            mask[valid] = mapping[indices[valid]] == rod
            force = float(impulses.numpy()[mask, 2].sum(dtype=np.float64) / args.dt)
            if not math.isfinite(force):
                raise RuntimeError(f"nonfinite force at tick {tick}")
            trace.append(
                {
                    "time_s": (tick + 1) * args.dt,
                    "depth_m": (tick + 1) * speed * args.dt,
                    "force_z_n": force,
                }
            )
            if tick % 50 == 0 or tick == steps - 1:
                q = state.particle_q.numpy()
                if not np.isfinite(q).all():
                    raise RuntimeError(f"nonfinite soil at tick {tick}")
                print(f"step {tick + 1}/{steps}; force {force:.4f} N", flush=True)
        depths = np.array([r["depth_m"] for r in trace])
        forces = np.array([r["force_z_n"] for r in trace])
        reference_force = np.interp(depths, condition["depth_m"], condition["resisting_force_n"])
        report = {
            "status": "exploratory force comparison; not independent physical validation",
            "source": identity,
            "environment": environment_info(),
            "reference_sha256": file_hash(args.data),
            "source_changed_during_run": identity["source_sha256"]
            != source_identity(Path.cwd())["source_sha256"],
            "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            "particle_count": n,
            "mass_kg": particle_mass * n,
            "force_mae_n": float(abs(forces - reference_force).mean()),
            "force_rmse_n": float(np.sqrt(((forces - reference_force) ** 2).mean())),
            "trace": trace,
            "limitations": [
                "uncalibrated friction",
                "no preparation/compaction history",
                "32-facet cylinder boundary",
                "no settling period",
                "no independent repeat split",
                "published derived force signal; uncertainty unresolved",
                "resolution not verified",
            ],
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(
            "data/raw/admission/rheometer/f4b98b71162ab4400fb3ad3bedb38a4b71a3a8b1/lab_data/VolumeFracTrials.csv"
        ),
    )
    parser.add_argument("--phi", type=float, default=0.57)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--voxel", type=float, default=0.009)
    parser.add_argument("--spacing", type=float, default=0.0045)
    parser.add_argument("--friction", type=float, default=0.6)
    parser.add_argument("--tool-friction", type=float, default=0.5)
    parser.add_argument("--depth", type=float, default=0.07)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        run(args)
    except Exception as error:
        (args.output / "failure.json").write_text(
            json.dumps(
                {
                    "status": "failed",
                    "reason": str(error),
                    "source": source_identity(Path.cwd()),
                    "config": {
                        k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
                    },
                },
                indent=2,
            )
        )
        raise
