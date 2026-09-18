"""Measure command-order invariance and shared-domain response; not physical validation."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from excavation_sim.backends.newton_shared import NewtonSharedToolWorld
from excavation_sim.core import ToolCommand
from excavation_sim.provenance import environment_info, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_identity(Path.cwd())
    world = NewtonSharedToolWorld()
    cases = []
    try:
        command_buffers_equal = True
        for reverse, second_moves in [(False, True), (True, True), (False, True), (False, False)]:
            observations = world.reset_agents(0)
            # A missing agent must reject the entire action before time advances.
            try:
                world.step_agents({"tool_0": ToolCommand((0, 0, 0))})
                raise AssertionError("partial command was accepted")
            except ValueError:
                assert world.tick == 0
            trace = []
            for _ in range(100):
                commands = {"tool_0": ToolCommand((0, 0, -0.10)),
                            "tool_1": ToolCommand((0, 0, -0.08 if second_moves else 0))}
                if reverse:
                    commands = dict(reversed(list(commands.items())))
                normal = world._command_forces(commands).copy()
                swapped = world._command_forces(dict(reversed(list(commands.items())))).copy()
                command_buffers_equal &= np.array_equal(normal, swapped)
                observations = world.step_agents(commands)
                diagnostics = world.diagnostics()
                if not diagnostics.finite or diagnostics.escaped_mass_kg > 0:
                    raise RuntimeError("invalid shared-world state")
                trace.append({"observations": {k: asdict(v) for k, v in observations.items()},
                              "loads": world.agent_loads(), "diagnostics": asdict(diagnostics)})
            cases.append({"reversed_mapping": reverse, "second_moves": second_moves,
                          "trace": trace})
            (args.output / f"case-{len(cases)}.json").write_text(json.dumps(cases[-1]))
        def vectors(case):
            return np.array([[*row["observations"][name]["tool_position_m"],
                              *row["observations"][name]["soil_force_n"]]
                             for row in case["trace"] for name in world.agent_ids])
        difference = float(np.max(abs(vectors(cases[0]) - vectors(cases[1]))))
        def differences(a, b):
            return {field: max(float(np.max(abs(
                np.asarray(x["observations"][name][field]) -
                np.asarray(y["observations"][name][field]))))
                for x, y in zip(a["trace"], b["trace"], strict=True)
                for name in world.agent_ids)
                for field in ("tool_position_m", "tool_velocity_m_s", "soil_force_n")}
        report = {"source": source, "environment": environment_info(),
                  "config": asdict(world.config),
                  "source_changed": source["source_sha256"] !=
                                    source_identity(Path.cwd())["source_sha256"],
                  "command_order_max_absolute_difference": difference,
                  "command_order_exact_match": difference == 0,
                  "same_state_command_buffers_exact_match": bool(command_buffers_equal),
                  "same_order_repeat_max_absolute_difference":
                      float(np.max(abs(vectors(cases[0]) - vectors(cases[2])))),
                  "reversed_order_differences_by_channel": differences(cases[0], cases[1]),
                  "same_order_differences_by_channel": differences(cases[0], cases[2]),
                  "both_tools_contacted_soil": all(any(
                      np.linalg.norm(row["observations"][name]["soil_force_n"]) > 1
                      for row in cases[0]["trace"]) for name in world.agent_ids),
                  "second_command_response_max_absolute_difference":
                      float(np.max(abs(vectors(cases[0]) - vectors(cases[3])))),
                  "claims": "Same-device component check. Mixed position/force maximum is "
                            "only an exact-equality diagnostic; not a physical error metric."}
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps({k: v for k, v in report.items() if k != "source"}, indent=2))
        return int(not report["command_order_exact_match"] or
                   not report["both_tools_contacted_soil"])
    finally:
        world.close()


if __name__ == "__main__":
    raise SystemExit(main())
