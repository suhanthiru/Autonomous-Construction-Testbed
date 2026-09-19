"""Versioned, engine-independent scenario specifications and deterministic preparation."""

import json
import math
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from excavation_sim.provenance import fingerprint


@dataclass(frozen=True)
class Scenario:
    name: str
    seed: int
    terrain: str = "flat"
    friction: float = 0.6
    density_kg_m3: float = 1600.0
    roughness_m: float = 0.0
    obstacle: str = "none"
    version: int = 1

    def __post_init__(self):
        if (
            self.version != 1
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", self.name)
            or type(self.seed) is not int
            or self.seed < 0
        ):
            raise ValueError("invalid scenario identity")
        if self.terrain not in {"flat", "slope", "mound"}:
            raise ValueError("unsupported terrain")
        if self.obstacle not in {"none", "dynamic", "anchored"}:
            raise ValueError("unsupported obstacle condition")
        if not (
            0.35 <= self.friction <= 0.9
            and 1400 <= self.density_kg_m3 <= 1800
            and 0 <= self.roughness_m <= 0.01
        ):
            raise ValueError("outside declared development configuration envelope")

    @property
    def identity(self):
        return fingerprint(asdict(self))


def particle_positions(scenario: Scenario, spacing: float):
    """Original procedural preparation, not a measured or equilibrated soil bed."""
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError("particle spacing must be finite and positive")
    count = round(0.4 / spacing)
    if not math.isclose(count * spacing, 0.4):
        raise ValueError("particle spacing must divide the bed width")
    rng = random.Random(f"scenario-v1:{scenario.seed}:terrain")
    points = []
    for ix in range(count):
        x = -0.2 + (ix + 0.5) * spacing
        for iy in range(count):
            y = -0.2 + (iy + 0.5) * spacing
            top = 0.2
            if scenario.terrain == "slope":
                top += 0.2 * x
            elif scenario.terrain == "mound":
                top = 0.15 + 0.1 * math.exp(-(x * x + y * y) / 0.015)
            top += rng.uniform(-scenario.roughness_m, scenario.roughness_m)
            for iz in range(max(0, math.floor(top / spacing + 1e-9))):
                z = (iz + 0.5) * spacing
                # Clear the rigid obstacle volume including half a particle spacing.
                if scenario.obstacle != "none" and (
                    abs(x + 0.02) < 0.04 + spacing / 2
                    and abs(y) < 0.04 + spacing / 2
                    and abs(z - 0.10) < 0.04 + spacing / 2
                ):
                    continue
                points.append((x, y, z))
    return points


def load_suite(path: Path):
    suite = json.loads(path.read_text(encoding="utf-8"))
    payload = {k: v for k, v in suite.items() if k != "sha256"}
    if suite.get("version") != 1 or suite.get("sha256") != fingerprint(payload):
        raise ValueError("scenario suite version or checksum mismatch")
    names, identities = set(), set()
    if set(suite["splits"]) != {"train", "development", "test"}:
        raise ValueError("suite must declare train, development and test splits")
    for split in suite["splits"].values():
        if not split:
            raise ValueError("scenario splits cannot be empty")
        for data in split:
            scenario = Scenario(**data)
            physical = asdict(scenario)
            physical.pop("name")
            if scenario.roughness_m == 0:
                physical.pop("seed")
            identity = fingerprint(physical)
            if scenario.name in names or identity in identities:
                raise ValueError("duplicate scenario across suite splits")
            names.add(scenario.name)
            identities.add(identity)
    return suite
