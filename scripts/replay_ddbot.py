"""Exploratory prescribed-motion replay of pinned DDBot sand trial 0.

This implements a conditional terrain comparison, not a physical-validation pass.
"""

import argparse
import json
import math
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM

from excavation_sim.actuation import ticks_per_update
from excavation_sim.datasets import ddbot_actions, file_hash, read_triangle_obj, surface_height_map
from excavation_sim.provenance import environment_info, source_identity


def replay(args):
    if not all(
        math.isfinite(v) and v > 0 for v in (args.dt, args.voxel, args.spacing, args.density)
    ):
        raise ValueError("time, spatial scales, and density must be finite and positive")
    if not all(
        math.isfinite(v) and v >= 0
        for v in (args.friction, args.tool_friction, args.wall_friction, args.air_drag)
    ):
        raise ValueError("friction and drag must be finite and nonnegative")
    if args.limit_actions < 0:
        raise ValueError("limit_actions must be nonnegative")
    identity = source_identity(Path.cwd())
    root = args.data
    actions = ddbot_actions(root, args.trial)
    full_action_count = len(actions)
    if args.limit_actions:
        actions = actions[: args.limit_actions]
    substeps = ticks_per_update(args.dt, 0.01)
    spacing = args.spacing
    dims = [ticks_per_update(spacing, length) for length in (0.28, 0.28, 0.07)]
    mesh_path = root / "simulator/doma/assets/meshes/processed/ShovelEEF-ShovelEEF.obj"
    vertices, faces = read_triangle_obj(mesh_path)
    target_path = (
        root
        / "data/system-identification-targets/sand"
        / f"pcd_{args.trial}_cropped_norm_z_aligned_height_map-res40.npy"
    )
    target = np.load(target_path, allow_pickle=False)
    wp.config.kernel_cache_dir = str(Path(".cache/warp").resolve())
    wp.init()
    with wp.ScopedDevice("cuda:0"):
        builder = newton.ModelBuilder()
        SolverImplicitMPM.register_custom_attributes(builder)
        position = np.array([0.2, 0.2, 0.205], dtype=np.float64)
        # Upstream uses extrinsic z-y-x Euler angles (90,180,0), in degrees.
        rotation = wp.quat_from_axis_angle(wp.vec3(0, 1, 0), math.pi) * wp.quat_from_axis_angle(
            wp.vec3(0, 0, 1), math.pi / 2
        )
        tool = builder.add_body(xform=wp.transform(wp.vec3(position), rotation), is_kinematic=True)
        tool_cfg = newton.ModelBuilder.ShapeConfig(density=0, mu=args.tool_friction)
        if args.tool_geometry == "mesh":
            builder.add_shape_mesh(tool, mesh=newton.Mesh(vertices, faces), cfg=tool_cfg)
        else:
            low, high = vertices.min(0), vertices.max(0)
            half = (high - low) / 2
            builder.add_shape_box(
                tool,
                xform=wp.transform(wp.vec3((high + low) / 2), wp.quat_identity()),
                hx=float(half[0]),
                hy=float(half[1]),
                hz=float(half[2]),
                cfg=tool_cfg,
            )
        builder.add_ground_plane(
            height=0.015, cfg=newton.ModelBuilder.ShapeConfig(mu=args.wall_friction)
        )
        # Plane control avoids thin walls smaller than a voxel; its infinite height is explicit.
        if args.boundary == "planes":
            for plane in [(1, 0, 0, -0.06), (-1, 0, 0, 0.34), (0, 1, 0, -0.06), (0, -1, 0, 0.34)]:
                builder.add_shape_plane(
                    plane=tuple(float(v) for v in plane),
                    width=0.0,
                    length=0.0,
                    cfg=newton.ModelBuilder.ShapeConfig(mu=args.wall_friction),
                )
        # Finite walls are retained as a diagnostic alternative; no top ceiling.
        for center, half in [
            ((0.055, 0.2, 0.07), (0.005, 0.145, 0.055)),
            ((0.345, 0.2, 0.07), (0.005, 0.145, 0.055)),
            ((0.2, 0.055, 0.07), (0.145, 0.005, 0.055)),
            ((0.2, 0.345, 0.07), (0.145, 0.005, 0.055)),
        ]:
            if args.boundary == "boxes":
                builder.add_shape_box(
                    -1,
                    xform=wp.transform(wp.vec3(center), wp.quat_identity()),
                    hx=half[0],
                    hy=half[1],
                    hz=half[2],
                    cfg=newton.ModelBuilder.ShapeConfig(mu=args.wall_friction),
                )
        builder.add_particle_grid(
            pos=wp.vec3(0.06 + spacing / 2, 0.06 + spacing / 2, 0.015 + spacing / 2),
            rot=wp.quat_identity(),
            vel=wp.vec3(0),
            dim_x=dims[0],
            dim_y=dims[1],
            dim_z=dims[2],
            cell_x=spacing,
            cell_y=spacing,
            cell_z=spacing,
            mass=args.density * spacing**3,
            radius_mean=spacing / 2,
            jitter=0,
            custom_attributes={"mpm:friction": args.friction},
        )
        model = builder.finalize()
        config = SolverImplicitMPM.Config()
        config.voxel_size = args.voxel
        config.grid_type = "fixed"
        config.grid_padding = 8
        config.max_active_cell_count = 1 << 17
        config.max_iterations = 100
        config.tolerance = 1e-5
        config.strain_basis = "P0"
        config.critical_fraction = 0.0
        config.air_drag = args.air_drag
        solver = SolverImplicitMPM(model, config)
        state, output = model.state(), model.state()
        solver.setup_collider(body_mass=wp.zeros_like(model.body_mass), body_q=state.body_q)
        initial_particles = state.particle_q.numpy()
        traces = []
        for step, action in enumerate(actions):
            for _ in range(substeps):
                delta = action[:3] / substeps
                angular = action[3:] / substeps
                # Position-control rotation increments are rotation vectors, in radians.
                angle = float(np.linalg.norm(angular))
                dq = (
                    wp.quat_from_axis_angle(wp.vec3(angular / angle), angle)
                    if angle
                    else wp.quat_identity()
                )
                state.body_q.assign(np.array([[*position, *rotation]], dtype=np.float32))
                state.body_qd.assign(
                    np.array(
                        [
                            [
                                *(action[:3] / 0.01),
                                *wp.quat_rotate(rotation, wp.vec3(action[3:] / 0.01)),
                            ]
                        ],
                        dtype=np.float32,
                    )
                )
                solver.step(state, output, None, None, args.dt)
                state, output = output, state
                position += delta
                rotation = wp.normalize(rotation * dq)
            points = state.particle_q.numpy()
            velocities = state.particle_qd.numpy()
            if not np.isfinite(points).all():
                raise RuntimeError(f"nonfinite particles after action {step}")
            with (args.output / "trace.jsonl").open("a", encoding="utf-8") as trace_stream:
                trace_stream.write(
                    json.dumps(
                        {
                            "action": step + 1,
                            "max_speed_m_s": float(np.linalg.norm(velocities, axis=1).max()),
                            "bounds_m": [points.min(0).tolist(), points.max(0).tolist()],
                        },
                        allow_nan=False,
                    )
                    + "\n"
                )
            if step % 25 == 0 or step == len(actions) - 1:
                traces.append(
                    {
                        "action": step + 1,
                        "tool_position_m": position.tolist(),
                        "soil_min_m": points.min(0).tolist(),
                        "soil_max_m": points.max(0).tolist(),
                    }
                )
                print(f"action {step + 1}/{len(actions)}", flush=True)
        points = state.particle_q.numpy()
        height = surface_height_map(points, spacing / 2)
        error = height - target
        np.save(args.output / "particles.npy", points, allow_pickle=False)
        np.save(args.output / "height.npy", height, allow_pickle=False)
        initial_height = surface_height_map(initial_particles, spacing / 2)
        report = {
            "status": "exploratory replay; not physically validated",
            "trial": args.trial,
            "complete_trajectory": len(actions) == full_action_count,
            "role": "development" if args.trial == 0 else "evaluation",
            "source": identity,
            "environment": environment_info(),
            "source_changed_during_run": identity["source_sha256"]
            != source_identity(Path.cwd())["source_sha256"],
            "config": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in vars(args).items()
            },
            "input_hashes": {
                "mesh": file_hash(mesh_path),
                "target": file_hash(target_path),
                "actions": file_hash(
                    root / f"data/trajectories/sys_id_sim_{args.trial}_pos-dt_0.01.npy"
                ),
            },
            "mae_m": float(np.abs(error).mean()),
            "rmse_m": float(np.sqrt((error**2).mean())),
            "unchanged_initial_surface_mae_m": float(np.abs(initial_height - target).mean()),
            "empty_surface_cells": int((height == 0).sum()),
            "particle_count": len(points),
            "trace": traces,
            "limitations": [
                "planned rather than measured tool motion",
                "uncalibrated Newton material",
                "uniform initial bed inferred from published apparatus",
                "no acceptance tolerance from repeat trials",
                "boundary geometry is an explicit approximation; see config.boundary",
                "no initial settling stage",
            ],
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/raw/admission/ddbot/e642f7c73f37539c21161bd29669fa8d91912b88"),
    )
    parser.add_argument("--trial", type=int, choices=[0, 1], default=0)
    parser.add_argument("--dt", type=float, default=0.005)
    parser.add_argument("--voxel", type=float, default=0.014)
    parser.add_argument("--spacing", type=float, default=0.007)
    parser.add_argument("--friction", type=float, default=0.6)
    parser.add_argument("--tool-friction", type=float, default=0.5)
    parser.add_argument("--wall-friction", type=float, default=0.5)
    parser.add_argument("--density", type=float, default=1600)
    parser.add_argument("--air-drag", type=float, default=1.0)
    parser.add_argument("--tool-geometry", choices=["mesh", "box"], default="mesh")
    parser.add_argument("--boundary", choices=["planes", "boxes"], default="planes")
    parser.add_argument("--limit-actions", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        replay(args)
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
