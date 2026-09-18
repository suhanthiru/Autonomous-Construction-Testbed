"""Typed policy-facing episode loading; privileged evaluation files are not read."""

import json
from dataclasses import dataclass
from math import isclose, isfinite
from pathlib import Path

from excavation_sim.core import JointCommand, Observation, ToolCommand


@dataclass(frozen=True)
class Transition:
    observation: Observation
    command: ToolCommand | JointCommand
    next_observation: Observation
    duration_s: float


def observation_from_dict(data):
    data = dict(data)
    for key in ("tool_position_m", "tool_velocity_m_s", "soil_force_n"):
        values = data[key]
        if len(values) != 3 or not all(isfinite(v) for v in values):
            raise ValueError("invalid observation vector")
        data[key] = tuple(values)
    for key in ("joint_position_rad", "joint_velocity_rad_s"):
        data[key] = tuple(data.get(key, ()))
        if not all(isfinite(v) for v in data[key]):
            raise ValueError("invalid joint observation")
    if len(data["joint_position_rad"]) != len(data["joint_velocity_rad_s"]):
        raise ValueError("joint observation dimensions disagree")
    if type(data["tick"]) is not int or data["tick"] < 0:
        raise ValueError("invalid observation tick")
    if not isfinite(data["time_s"]) or data["time_s"] < 0:
        raise ValueError("invalid observation time")
    if not isfinite(data.get("sensor_age_s", 0.0)) or data.get("sensor_age_s", 0.0) < 0:
        raise ValueError("invalid sensor age")
    capture = data.get("sensor_capture_tick")
    if capture is not None and (type(capture) is not int or not 0 <= capture <= data["tick"]):
        raise ValueError("sensor capture cannot be in the future")
    if type(data.get("sensor_valid", True)) is not bool:
        raise ValueError("sensor validity must be boolean")
    return Observation(**data)


def load_episode(directory: Path, *, allow_incomplete: bool = False) -> list[Transition]:
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported episode schema")
    outcome_path = directory / "outcome.json"
    if not outcome_path.exists():
        if not allow_incomplete:
            raise ValueError("episode has no outcome; recording was interrupted")
        outcome = {"status": "interrupted", "last_tick": None}
    else:
        outcome = json.loads(outcome_path.read_text())
    if outcome.get("status") != "completed" and not allow_incomplete:
        raise ValueError("episode did not complete")
    result = []
    for line in (directory / "transitions.jsonl").read_text().splitlines():
        row = json.loads(line)
        before = observation_from_dict(row["observation"])
        after = observation_from_dict(row["next_observation"])
        command = row["command"]
        if set(command) == {"velocity_targets"}:
            action = JointCommand(tuple(command["velocity_targets"]))
        elif set(command) == {"velocity_m_s"}:
            action = ToolCommand(tuple(command["velocity_m_s"]))
        else:
            raise ValueError("unknown or mixed action representation")
        duration = row["duration_s"]
        if after.tick <= before.tick or not isfinite(duration) or duration <= 0:
            raise ValueError("nonadvancing transition")
        if not isclose(after.time_s - before.time_s, duration, abs_tol=1e-12, rel_tol=1e-10):
            raise ValueError("transition duration disagrees with observation clock")
        if result and before != result[-1].next_observation:
            raise ValueError("episode observation chain is discontinuous")
        result.append(Transition(before, action, after, duration))
    if (
        result
        and outcome["last_tick"] is not None
        and result[-1].next_observation.tick != outcome["last_tick"]
    ):
        raise ValueError("outcome does not match final transition")
    return result
