"""GPU height reduction with conservative rigid-box occlusion for an ideal overhead sensor."""

import newton
import warp as wp

from excavation_sim.surface import SurfacePacket


@wp.kernel
def reduce_surface(points: wp.array(dtype=wp.vec3), heights: wp.array(dtype=float),
                   origin: wp.vec2, cell: float, width: int, height: int):
    p = points[wp.tid()]
    x = int(wp.floor((p[0] - origin[0]) / cell))
    y = int(wp.floor((p[1] - origin[1]) / cell))
    if x >= 0 and x < width and y >= 0 and y < height and wp.isfinite(p[2]):
        wp.atomic_max(heights, y * width + x, p[2])


@wp.kernel
def mask_surface(heights: wp.array(dtype=float), visible: wp.array(dtype=int),
                 body_q: wp.array(dtype=wp.transform), shape_body: wp.array(dtype=int),
                 shape_q: wp.array(dtype=wp.transform), shape_scale: wp.array(dtype=wp.vec3),
                 shape_type: wp.array(dtype=int), shape_count: int, box_type: int,
                 origin: wp.vec2, cell: float, width: int):
    index = wp.tid()
    z = heights[index]
    valid = int(z > -1.0e9)
    x0 = origin[0] + float(index % width) * cell
    y0 = origin[1] + float(index // width) * cell
    # Whole-cell conservative mask: any box AABB overlapping the column above its
    # surface blocks the reading. This intentionally over-occludes rotated boxes.
    for s in range(shape_count):
        if shape_type[s] == box_type:
            pose = shape_q[s]
            if shape_body[s] >= 0:
                pose = wp.transform_multiply(body_q[shape_body[s]], pose)
            lower = wp.vec3(1.0e10)
            upper = wp.vec3(-1.0e10)
            for corner in range(8):
                sign = wp.vec3(float(2 * (corner % 2) - 1),
                               float(2 * ((corner // 2) % 2) - 1),
                               float(2 * ((corner // 4) % 2) - 1))
                point = wp.transform_point(pose, wp.cw_mul(sign, shape_scale[s]))
                lower = wp.min(lower, point)
                upper = wp.max(upper, point)
            if (upper[0] >= x0 and lower[0] <= x0 + cell and upper[1] >= y0
                    and lower[1] <= y0 + cell and upper[2] >= z):
                valid = 0
    visible[index] = valid
    if valid == 0:
        heights[index] = 0.0


def capture_surface(world) -> SurfacePacket:
    world._require_ready()
    width, height, cell = 32, 32, 0.025
    origin = (-0.4, -0.4)
    with wp.ScopedDevice(world.device):
        heights = wp.full(width * height, -1.0e10, dtype=float)
        visible = wp.zeros(width * height, dtype=int)
        model = world.model
        supported = {int(newton.GeoType.BOX), int(newton.GeoType.PLANE)}
        if any(int(kind) not in supported for kind in model.shape_type.numpy()):
            raise ValueError("surface occlusion supports box and plane scenes only")
        if model.particle_count:
            wp.launch(reduce_surface, dim=model.particle_count,
                      inputs=[world.state.particle_q, heights, wp.vec2(*origin),
                              cell, width, height])
        wp.launch(mask_surface, dim=width * height,
                  inputs=[heights, visible, world.state.body_q, model.shape_body,
                          model.shape_transform, model.shape_scale, model.shape_type,
                          model.shape_count, int(newton.GeoType.BOX), wp.vec2(*origin),
                          cell, width])
        return SurfacePacket(origin, cell, width, height, tuple(map(float, heights.numpy())),
                             tuple(map(bool, visible.numpy())))
