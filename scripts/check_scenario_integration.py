"""Executed obstacle, observation-access, reset and inspection-side-effect checks."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from excavation_sim.backends.newton_scenario import NewtonScenarioWorld
from excavation_sim.core import JointCommand
from excavation_sim.provenance import environment_info, source_identity
from excavation_sim.scenarios import Scenario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_identity(Path.cwd())
    reports = []
    for mode in ("dynamic", "anchored"):
        world = NewtonScenarioWorld(Scenario("integration-" + mode, 0, obstacle=mode))
        try:
            observation = world.reset(0)
            before = world.inspection_state()
            poses = before["body_poses"].copy()
            loads = []
            for _ in range(100):
                observation = world.step(JointCommand((0, 0, 0, 0)))
                d = world.diagnostics()
                assert d.finite and d.escaped_mass_kg == 0
                assert len(observation.joint_position_rad) == 4
                assert "obstacle" not in asdict(observation)
                loads.append(world._body_forces[world.obstacle_body].tolist())
            state = world.inspection_state()
            tick = world.tick
            world.capture_surface()
            after = world.inspection_state()
            assert world.tick == tick
            np.testing.assert_array_equal(state["body_poses"], after["body_poses"])
            np.testing.assert_array_equal(state["particles"], after["particles"])
            displacement = float(
                np.linalg.norm(
                    state["body_poses"][world.obstacle_body, :3] - poses[world.obstacle_body, :3]
                )
            )
            if mode == "anchored":
                assert displacement < 1e-7
            else:
                assert displacement > 1e-7
            reports.append(
                {
                    "condition": mode,
                    "displacement_m": displacement,
                    "peak_obstacle_soil_force_n": float(np.linalg.norm(loads, axis=1).max()),
                    "diagnostics": asdict(d),
                    "runtime_model": world.runtime_metadata(),
                    "inspection_did_not_mutate_state": True,
                    "passive_joint_coordinates_excluded_from_observation": True,
                }
            )
        finally:
            world.close()
    report = {
        "source": source,
        "environment": environment_info(),
        "cases": reports,
        "source_changed": source["source_sha256"] != source_identity(Path.cwd())["source_sha256"],
        "claim": "Obstacle settling and load coupling; not excavation success or rock validation",
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print("Scenario integration checks passed")


if __name__ == "__main__":
    main()
