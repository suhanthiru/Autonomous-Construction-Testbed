"""Offline privileged inspection; sampled particles are for display only."""

import json
from dataclasses import asdict
from pathlib import Path


class InspectionRecorder:
    def __init__(self, particle_stride: int = 4):
        if type(particle_stride) is not int or particle_stride < 1:
            raise ValueError("particle stride must be a positive integer")
        self.stride = particle_stride
        self.frames = []
        self.shapes = []

    def __call__(self, world, observation):
        snapshot = world.inspection_state()
        if not self.frames:
            self.shapes = snapshot.get("shapes", [])
        self.frames.append(
            {
                "observation": asdict(observation),
                "bodies": snapshot["body_poses"].tolist(),
                "particles": snapshot["particles"][:: self.stride].tolist(),
            }
        )

    def write(self, output: Path):
        template = Path(__file__).with_name("inspection.html").read_text(encoding="utf-8")
        data = json.dumps(
            {"frames": self.frames, "particle_stride": self.stride, "shapes": self.shapes},
            allow_nan=False,
        )
        with output.open("x", encoding="utf-8") as stream:
            stream.write(template.replace("__EPISODE_DATA__", data.replace("<", "\\u003c")))
