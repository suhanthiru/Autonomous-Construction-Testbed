import json
from dataclasses import asdict
from pathlib import Path

import pytest

from excavation_sim.provenance import fingerprint
from excavation_sim.scenarios import Scenario, load_suite, particle_positions


def test_preparation_reproducible_and_obstacle_volume_cleared():
    scenario = Scenario("rough", 7, terrain="mound", roughness_m=0.005)
    assert particle_positions(scenario, 0.02) == particle_positions(scenario, 0.02)
    flat = particle_positions(Scenario("flat", 0), 0.02)
    assert len(flat) == 4000
    obstacle = particle_positions(Scenario("rock", 0, obstacle="dynamic"), 0.02)
    assert len(obstacle) < len(flat)
    assert not any(
        abs(x + 0.02) < 0.05 and abs(y) < 0.05 and abs(z - 0.1) < 0.05 for x, y, z in obstacle
    )


def test_suite_detects_tampering_and_duplicate_physical_splits(tmp_path):
    suite = load_suite(Path("scenarios/v1/suite.json"))
    suite["splits"]["test"][0]["friction"] = 0.8
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError, match="checksum"):
        load_suite(path)
    suite["splits"]["test"][0] = asdict(Scenario("renamed", 999))
    suite["sha256"] = fingerprint({k: v for k, v in suite.items() if k != "sha256"})
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError, match="duplicate"):
        load_suite(path)
