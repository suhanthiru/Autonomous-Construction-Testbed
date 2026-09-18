"""Offline privileged inspection; sampled particles are for display only."""

import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path


class InspectionRecorder:
    def __init__(self, particle_stride: int = 4, frame_interval_s: float = 0.1):
        if type(particle_stride) is not int or particle_stride < 1:
            raise ValueError("particle stride must be a positive integer")
        self.stride = particle_stride
        if not isfinite(frame_interval_s) or frame_interval_s <= 0:
            raise ValueError("display frame interval must be finite and positive")
        self.frame_interval_s = frame_interval_s
        self.frames = []
        self.shapes = []

    def __call__(self, world, observation):
        if self.frames and observation.time_s - self.frames[-1]["observation"]["time_s"] < (
            self.frame_interval_s - 1e-9
        ):
            return
        snapshot = world.inspection_state()
        if not self.frames:
            self.shapes = snapshot.get("shapes", [])
        self.frames.append(
            {
                "observation": asdict(observation),
                "bodies": snapshot["body_poses"].astype(float).round(5).tolist(),
                "particles": snapshot["particles"][:: self.stride].astype(float).round(5).tolist(),
            }
        )

    def write(self, output: Path):
        template = Path(__file__).with_name("inspection.html").read_text(encoding="utf-8")
        data = json.dumps(
            {"frames": self.frames, "particle_stride": self.stride, "shapes": self.shapes,
             "frame_interval_s": self.frame_interval_s},
            allow_nan=False,
            separators=(",", ":"),
        )
        with output.open("x", encoding="utf-8") as stream:
            stream.write(template.replace("__EPISODE_DATA__", data.replace("<", "\\u003c")))
