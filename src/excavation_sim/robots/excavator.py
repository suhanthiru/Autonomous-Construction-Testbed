"""Procedural bench-scale fixed-base excavator, asset version 1.

Original primitive geometry; not a model of a commercial machine. SI units.
Joint order: slew (Z), boom (Y), stick (Y), bucket (Y). Quaternion order XYZW.
"""

from dataclasses import dataclass

import newton
import warp as wp


@dataclass(frozen=True)
class ExcavatorAsset:
    bodies: tuple[int, ...]
    joints: tuple[int, ...]
    bucket_body: int
    initial_q: tuple[float, ...] = (0.0, -0.5, 1.0, -0.5)
    effort_limits_nm: tuple[float, ...] = (80.0, 120.0, 80.0, 40.0)
    lower_limits_rad: tuple[float, ...] = (-1.5, -1.2, -0.3, -1.8)
    upper_limits_rad: tuple[float, ...] = (1.5, 0.8, 1.8, 1.2)


def add_excavator(builder) -> ExcavatorAsset:
    bodies, joints = [], []
    lower, upper = (-1.5, -1.2, -0.3, -1.8), (1.5, 0.8, 1.8, 1.2)
    efforts = (80.0, 120.0, 80.0, 40.0)
    anchors = [(-0.5, 0.0, 0.35), (0.0, 0.0, 0.0), (0.4, 0.0, 0.0), (0.35, 0.0, 0.0)]
    names = ("slew", "boom", "stick", "bucket")
    for i, name in enumerate(names):
        body = builder.add_link(label=name)
        parent = bodies[-1] if bodies else -1
        joint = builder.add_joint_revolute(
            parent,
            body,
            parent_xform=wp.transform(wp.vec3(*anchors[i]), wp.quat_identity()),
            child_xform=wp.transform_identity(),
            axis=wp.vec3(0, 0, 1) if i == 0 else wp.vec3(0, 1, 0),
            limit_lower=lower[i],
            limit_upper=upper[i],
            limit_ke=1e4,
            limit_kd=100.0,
            target_ke=0.0,
            target_kd=0.0,
            effort_limit=efforts[i],
            velocity_limit=0.6,
            actuator_mode=newton.JointTargetMode.EFFORT,
            label=name,
        )
        bodies.append(body)
        joints.append(joint)
        cfg = newton.ModelBuilder.ShapeConfig(density=1200.0, mu=0.5)
        if i == 0:
            builder.add_shape_box(body, hx=0.06, hy=0.06, hz=0.05, cfg=cfg)
        elif i < 3:
            length = 0.4 if i == 1 else 0.35
            builder.add_shape_box(
                body,
                xform=wp.transform(wp.vec3(length / 2, 0, 0), wp.quat_identity()),
                hx=length / 2,
                hy=0.025,
                hz=0.025,
                cfg=cfg,
            )
        else:
            # Open top and front (+X): floor, back wall, and two side walls.
            for center, half in [
                ((0.06, 0.0, -0.06), (0.10, 0.10, 0.02)),
                ((-0.02, 0.0, 0.0), (0.02, 0.10, 0.06)),
                ((0.06, -0.08, 0.0), (0.10, 0.02, 0.06)),
                ((0.06, 0.08, 0.0), (0.10, 0.02, 0.06)),
            ]:
                builder.add_shape_box(
                    body,
                    xform=wp.transform(wp.vec3(*center), wp.quat_identity()),
                    hx=half[0],
                    hy=half[1],
                    hz=half[2],
                    cfg=cfg,
                )
    builder.add_articulation(joints, label="fixed_base_excavator_v1")
    return ExcavatorAsset(tuple(bodies), tuple(joints), bodies[-1])
