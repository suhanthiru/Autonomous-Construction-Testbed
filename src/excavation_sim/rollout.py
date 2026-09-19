"""Headless policy execution with explicit budgets and failure-preserving recording."""

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from excavation_sim.core import Policy, World
from excavation_sim.provenance import environment_info, source_identity
from excavation_sim.recording import EpisodeWriter
from excavation_sim.validation import validation_snapshot


def rollout(
    world: World,
    policy: Policy,
    directory: Path,
    *,
    seed: int,
    actions: int,
    config: dict,
    source_root: Path,
    inspect: Callable | None = None,
    task=None,
) -> dict:
    if type(actions) is not int or actions < 1:
        raise ValueError("actions must be a positive integer")
    started = perf_counter()
    identity = source_identity(source_root)
    writer = EpisodeWriter(
        directory,
        {
            "schema_version": 1,
            "seed": seed,
            "action_budget": actions,
            "backend": asdict(world.info),
            "clock": asdict(world.clock),
            "config": config,
            "source": identity,
            "environment": environment_info(),
            "observation_access": {
                "channels": "tool pose, velocity, action-averaged soil force; optional joints",
                "sensors": config.get("sensors", "ideal instantaneous"),
                "privileged_evaluation_excluded": True,
            },
            "physical_validation": "not validated",
            "validation_snapshot": validation_snapshot(source_root),
        },
    )
    completed = 0
    task_result = None
    try:
        observation = world.reset(seed)
        if hasattr(world, "runtime_metadata"):
            (directory / "runtime-model.json").write_text(
                json.dumps(world.runtime_metadata(), indent=2), encoding="utf-8"
            )
        policy.reset(seed)
        if task is not None:
            task.reset()
        if inspect is not None:
            inspect(world, observation)
        for _ in range(actions):
            command = policy.act(observation)
            after = world.step(command)
            diagnostics = world.diagnostics()
            evaluation = (
                world.evaluation_observation()
                if hasattr(world, "evaluation_observation")
                else after
            )
            if task is not None:
                task_result = task.evaluate(evaluation, diagnostics)
            writer.append(
                observation,
                command,
                after,
                diagnostics,
                task_result,
                raw_soil_force_n=evaluation.soil_force_n,
            )
            completed += 1
            if not diagnostics.finite:
                raise RuntimeError("nonfinite world diagnostics")
            if diagnostics.escaped_mass_kg > 0:
                raise RuntimeError("material left the declared audit envelope")
            observation = after
            if inspect is not None:
                inspect(world, observation)
            if task_result is not None and (task_result.terminated or task_result.truncated):
                break
        reason = "action budget exhausted; not a task-success claim"
        if task_result is not None:
            reason = (
                "task succeeded" if task_result.success else "task budget exhausted without success"
            )
        writer.close("completed", reason)
        return {
            "actions": completed,
            "task_result": asdict(task_result) if task_result is not None else None,
            "simulated_time_s": observation.time_s,
            "wall_time_s": perf_counter() - started,
            "source_changed": identity["source_sha256"]
            != source_identity(source_root)["source_sha256"],
        }
    except KeyboardInterrupt:
        writer.close("interrupted", "keyboard interrupt")
        raise
    except Exception as error:
        writer.close("failed", f"{type(error).__name__}: {error}")
        raise
    finally:
        world.close()
        if hasattr(policy, "events"):
            (directory / "policy-events.json").write_text(
                json.dumps(policy.events, indent=2), encoding="utf-8"
            )
