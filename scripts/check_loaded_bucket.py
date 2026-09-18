"""Dynamic preloaded bucket: distinguish carrying from excavation trajectory quality."""

import argparse
import json
from pathlib import Path

import newton
import numpy as np
import warp as wp

from excavation_sim.backends.newton_tool import NewtonToolWorld, ToolWorldConfig
from excavation_sim.core import ToolCommand
from excavation_sim.provenance import source_identity
from excavation_sim.robots.excavator import add_bucket


class LoadedBucketWorld(NewtonToolWorld):
    orientation_free = False

    def _add_robot(self, builder):
        body = builder.add_body(xform=wp.transform(wp.vec3(0, 0, 0.4), wp.quat_identity()))
        add_bucket(builder, body, newton.ModelBuilder.ShapeConfig(density=1200.0, mu=0.5))
        if self.orientation_free:
            return [body], [], body
        joint = builder.add_joint_prismatic(
            -1,
            body,
            axis=wp.vec3(0, 0, 1),
            parent_xform=wp.transform(wp.vec3(0, 0, 0.4), wp.quat_identity()),
            child_xform=wp.transform_identity(),
            target_ke=0.0,
            target_kd=0.0,
        )
        builder.add_articulation([joint], label="vertical_bucket_fixture")
        return [body], [joint], body

    def _add_soil(self, builder):
        builder.add_particle_grid(
            pos=wp.vec3(0.025, -0.025, 0.375),
            rot=wp.quat_identity(),
            vel=wp.vec3(0),
            dim_x=8,
            dim_y=6,
            dim_z=5 if self.config.with_soil else 0,
            cell_x=0.01,
            cell_y=0.01,
            cell_z=0.01,
            mass=0.0016,
            radius_mean=0.005,
            jitter=0.0,
            custom_attributes={"mpm:friction": 0.6},
        )


def main(args):
    if args.output.exists():
        raise FileExistsError(args.output)
    LoadedBucketWorld.orientation_free = args.orientation_free
    identity = source_identity(Path.cwd())
    results = []
    for soil in (False, True):
        world = LoadedBucketWorld(
            ToolWorldConfig(
                with_soil=soil,
                voxel_size_m=0.02,
                force_limit_n=100.0,
                grid_margin_m=args.grid_margin,
                max_active_cells=1 << 15,
            )
        )
        observation = world.reset(0)
        records = []
        status, reason = "completed", "scheduled motion finished"
        try:
            for _ in range(150):
                observation = world.step(
                    ToolCommand((0.0, 0.0, 0.15 if 1 <= observation.time_s < 2 else 0.0))
                )
                snapshot = world.inspection_state()
                pose = snapshot["body_poses"][0]
                transform = wp.transform(wp.vec3(*pose[:3]), wp.quat(*pose[3:]))
                # Inspection fixture only: explicit host transform of a small particle set.
                q = np.array(
                    [
                        list(wp.transform_point(wp.transform_inverse(transform), wp.vec3(*p)))
                        for p in snapshot["particles"]
                    ]
                ).reshape(-1, 3)
                inside = (
                    (q[:, 0] >= 0)
                    & (q[:, 0] <= 0.16)
                    & (abs(q[:, 1]) <= 0.06)
                    & (q[:, 2] >= -0.04)
                    & (q[:, 2] <= 0.06)
                )
                records.append(
                    {
                        "time_s": observation.time_s,
                        "height_m": observation.tool_position_m[2],
                        "soil_force_z_n": observation.soil_force_n[2],
                        "inside_mass_kg": float(inside.sum() * 0.0016),
                    }
                )
        except Exception as error:
            status, reason = "failed", f"{type(error).__name__}: {error}"
        finally:
            world.close()
        results.append({"with_soil": soil, "trace": records, "status": status, "reason": reason})
    output = args.output
    with output.open("x") as stream:
        json.dump(
            {
                "source": identity,
                "orientation_free": args.orientation_free,
                "grid_margin_m": args.grid_margin,
                "results": results,
                "source_changed": identity["source_sha256"]
                != source_identity(Path.cwd())["source_sha256"],
                "scope": "preloaded dynamic lift; not an excavation or physical-validation pass",
            },
            stream,
            indent=2,
        )

    return int(any(result["status"] != "completed" for result in results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orientation-free", action="store_true")
    parser.add_argument("--grid-margin", type=float, default=0.5)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
