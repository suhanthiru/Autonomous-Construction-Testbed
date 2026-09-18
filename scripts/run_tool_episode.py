"""Execute an external policy through the reusable experimental tool backend."""

import argparse
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

from excavation_sim.backends.newton_tool import NewtonToolWorld, ToolWorldConfig
from excavation_sim.inspection import InspectionRecorder
from excavation_sim.rollout import rollout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("experiments/tool_probe.py"))
    parser.add_argument("--policy-class", default="ProbePolicy")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--actions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--without-soil", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    # Explicit local extension code, chosen by the caller, not downloaded dataset code.
    spec = importlib.util.spec_from_file_location("experiment_policy", args.policy)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load policy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    policy = getattr(module, args.policy_class)()
    config = ToolWorldConfig(with_soil=not args.without_soil)
    inspection = InspectionRecorder() if args.inspect else None
    result = rollout(
        NewtonToolWorld(config),
        policy,
        args.output,
        seed=args.seed,
        actions=args.actions,
        config={
            "world": asdict(config),
            "policy_path": str(args.policy),
            "policy_class": args.policy_class,
        },
        source_root=Path.cwd(),
        inspect=inspection,
    )
    (args.output / "performance.json").write_text(json.dumps(result, indent=2))
    if inspection is not None:
        inspection.write(args.output / "inspection.html")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
