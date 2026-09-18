"""Headless policy execution with explicit budgets and failure-preserving recording."""

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from excavation_sim.core import Policy, World
from excavation_sim.provenance import environment_info, source_identity
from excavation_sim.recording import EpisodeWriter


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
            "observation_access": "ideal tool pose, velocity, action-averaged soil force",
            "physical_validation": "not validated",
        },
    )
    completed = 0
    try:
        observation = world.reset(seed)
        policy.reset(seed)
        if inspect is not None:
            inspect(world, observation)
        for _ in range(actions):
            command = policy.act(observation)
            after = world.step(command)
            diagnostics = world.diagnostics()
            writer.append(observation, command, after, diagnostics)
            completed += 1
            if not diagnostics.finite:
                raise RuntimeError("nonfinite world diagnostics")
            if diagnostics.escaped_mass_kg > 0:
                raise RuntimeError("material left the declared audit envelope")
            observation = after
            if inspect is not None:
                inspect(world, observation)
        writer.close("completed", "action budget exhausted; not a task-success claim")
        return {
            "actions": completed,
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
