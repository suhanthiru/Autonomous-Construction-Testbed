"""Explicit GPU integration check: reset, force bounds, and independent worlds."""

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from excavation_sim.backends.newton_tool import NewtonToolWorld, ToolWorldConfig
from excavation_sim.core import ToolCommand
from excavation_sim.provenance import environment_info, source_identity


def trajectory(world):
    initial = world.reset(11)
    observations = [asdict(initial)]
    for _ in range(5):
        observations.append(asdict(world.step(ToolCommand((0.0, 0.0, -0.1)))))
        d = world.diagnostics()
        assert d.finite and d.escaped_mass_kg == 0
        assert np.linalg.norm(d.actuator_force_n) <= world.config.force_limit_n + 1e-5
    return observations


if __name__ == "__main__":
    output = Path("runs/world-reset-check.json")
    if output.exists():
        raise FileExistsError(output)
    identity = source_identity(Path.cwd())
    results = []
    for soil in (False, True):
        world = NewtonToolWorld(ToolWorldConfig(with_soil=soil))
        first = trajectory(world)
        second = trajectory(world)
        a = np.array([list(o["tool_position_m"]) + list(o["soil_force_n"]) for o in first])
        b = np.array([list(o["tool_position_m"]) + list(o["soil_force_n"]) for o in second])
        # Repeated same-device execution, not a cross-device bitwise guarantee.
        np.testing.assert_allclose(a, b, atol=1e-6, rtol=1e-5)
        other = NewtonToolWorld(ToolWorldConfig(with_soil=soil))
        other.reset(8)
        before = other.inspection_state()
        world.step(ToolCommand((0.0, 0.0, 0.1)))
        after = other.inspection_state()
        np.testing.assert_array_equal(before["particles"], after["particles"])
        np.testing.assert_array_equal(before["body_poses"], after["body_poses"])
        world.close()
        other.close()
        results.append(
            {
                "with_soil": soil,
                "max_absolute_repeat_difference": float(abs(a - b).max()),
                "independent_world_unchanged": True,
                "observations": first,
            }
        )
    report = {
        "source": identity,
        "environment": environment_info(),
        "results": results,
        "source_changed": identity["source_sha256"] != source_identity(Path.cwd())["source_sha256"],
        "scope": "same-device reset, isolation, and actuator bounds; not physical validation",
    }
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(results, indent=2))
