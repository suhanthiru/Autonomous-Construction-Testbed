"""Execute an external policy through the reusable experimental tool backend."""

import argparse
import hashlib
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
    parser.add_argument("--machine", action="store_true")
    parser.add_argument("--task", choices=["probe", "scoop", "deposit"])
    parser.add_argument("--policy-kwargs", type=Path)
    parser.add_argument("--world-config", type=Path)
    parser.add_argument("--sensor-config", type=Path)
    parser.add_argument("--suite", type=Path)
    parser.add_argument("--scenario")
    parser.add_argument("--task-plugin", type=Path)
    parser.add_argument("--task-class")
    args = parser.parse_args()
    # Explicit local extension code, chosen by the caller, not downloaded dataset code.
    spec = importlib.util.spec_from_file_location("experiment_policy", args.policy)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load policy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kwargs = json.loads(args.policy_kwargs.read_text()) if args.policy_kwargs else {}
    policy = getattr(module, args.policy_class)(**kwargs)
    world_config = json.loads(args.world_config.read_text()) if args.world_config else {}
    if args.without_soil:
        world_config["with_soil"] = False
    config = ToolWorldConfig(**world_config)
    inspection = InspectionRecorder() if args.inspect else None
    scenario = None
    if args.suite:
        from excavation_sim.backends.newton_scenario import NewtonScenarioWorld
        from excavation_sim.scenarios import Scenario, load_suite

        suite = load_suite(args.suite)
        matches = [
            (split, row)
            for split, rows in suite["splits"].items()
            for row in rows
            if row["name"] == args.scenario
        ]
        if len(matches) != 1:
            raise ValueError("select exactly one named scenario from the suite")
        split, data = matches[0]
        scenario = Scenario(**data)
        args.seed = scenario.seed
        world = NewtonScenarioWorld(scenario, config)
        config = world.config
    elif args.scenario:
        raise ValueError("--scenario requires --suite")
    elif args.machine:
        from excavation_sim.backends.newton_excavator import NewtonExcavatorWorld

        world = NewtonExcavatorWorld(config)
    else:
        world = NewtonToolWorld(config)
    sensor_config = None
    if args.sensor_config:
        from excavation_sim.sensors import ObservedWorld, SensorConfig

        sensor_config = SensorConfig(**json.loads(args.sensor_config.read_text()))
        world = ObservedWorld(world, sensor_config)

    from excavation_sim.tasks import ExcavationTask, ExcavationTaskConfig

    task = (
        ExcavationTask(
            ExcavationTaskConfig(kind=args.task, time_limit_s=args.actions * config.action_dt_s)
        )
        if args.task
        else None
    )
    if args.task_plugin:
        if args.task or not args.task_class:
            raise ValueError("external task requires --task-class and excludes --task")
        task_spec = importlib.util.spec_from_file_location("experiment_task", args.task_plugin)
        task_module = importlib.util.module_from_spec(task_spec)
        task_spec.loader.exec_module(task_module)
        task = getattr(task_module, args.task_class)()
    artifacts = [args.policy]
    if args.task_plugin:
        artifacts.append(args.task_plugin)
    if "checkpoint" in kwargs:
        artifacts.append(Path(kwargs["checkpoint"]))
    result = rollout(
        world,
        policy,
        args.output,
        seed=args.seed,
        actions=args.actions,
        config={
            "world": asdict(config),
            "policy_path": str(args.policy),
            "policy_class": args.policy_class,
            "policy_kwargs": kwargs,
            "task": asdict(task.config) if task else None,
            "sensors": asdict(sensor_config) if sensor_config else "ideal instantaneous",
            "scenario": asdict(scenario) if scenario else None,
            "suite_sha256": suite["sha256"] if scenario else None,
            "split": split if scenario else None,
            "artifacts": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
        },
        source_root=Path.cwd(),
        inspect=inspection,
        task=task,
    )
    (args.output / "performance.json").write_text(json.dumps(result, indent=2))
    if hasattr(policy, "events"):
        (args.output / "policy-events.json").write_text(json.dumps(policy.events, indent=2))
    if inspection is not None:
        inspection.write(args.output / "inspection.html")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
