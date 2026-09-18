"""Explicit GPU occlusion and buried-point invariance check for the ideal height sensor."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import newton
import numpy as np
import warp as wp

from excavation_sim.backends.newton_surface import capture_surface
from excavation_sim.backends.newton_tool import NewtonToolWorld, ToolWorldConfig
from excavation_sim.provenance import environment_info, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_identity(Path.cwd())
    runtime = NewtonToolWorld(ToolWorldConfig(with_soil=False))
    with wp.ScopedDevice(runtime.device):
        points = np.array([[0.01, 0.01, 0.2], [0.21, 0.21, 0.2],
                           [0.21, 0.21, 0.05]], dtype=np.float32)
        state = SimpleNamespace(particle_q=wp.array(points, dtype=wp.vec3),
                                body_q=wp.array([wp.transform(wp.vec3(0, 0, 0.35),
                                                              wp.quat_identity())],
                                                dtype=wp.transform))
        model = SimpleNamespace(particle_count=3, shape_count=1,
                                shape_body=wp.array([0], dtype=int),
                                shape_transform=wp.array([wp.transform_identity()],
                                                         dtype=wp.transform),
                                shape_scale=wp.array([[0.06, 0.06, 0.04]], dtype=wp.vec3),
                                shape_type=wp.array([int(newton.GeoType.BOX)], dtype=int))
        world = SimpleNamespace(_require_ready=lambda: None, device=runtime.device,
                                model=model, state=state)
        first = capture_surface(world)
        def index(x, y):
            return int((y + 0.4) / 0.025) * 32 + int((x + 0.4) / 0.025)
        hidden, exposed = index(0.01, 0.01), index(0.21, 0.21)
        assert not first.visible[hidden] and first.heights_m[hidden] == 0
        assert first.visible[exposed] and abs(first.heights_m[exposed] - 0.2) < 1e-7
        points[0, 2], points[2, 2] = 0.15, 0.12
        state.particle_q.assign(points)
        assert capture_surface(world) == first
        state.body_q.assign([wp.transform(wp.vec3(-0.2, -0.2, 0.35), wp.quat_identity())])
        revealed = capture_surface(world)
        assert revealed.visible[hidden] and abs(revealed.heights_m[hidden] - 0.15) < 1e-7
        report = {"source": source, "environment": environment_info(),
                  "occluded_cells_zero": True, "buried_point_invariant": True,
                  "moving_occluder_reveals_surface": True,
                  "source_changed": source["source_sha256"] !=
                                    source_identity(Path.cwd())["source_sha256"],
                  "claim": "Ideal box-occluded column sensor only; not calibrated depth sensing"}
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print("GPU surface checks passed")


if __name__ == "__main__":
    main()
