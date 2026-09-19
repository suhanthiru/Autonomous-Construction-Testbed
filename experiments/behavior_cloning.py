"""Transparent ridge-regression behavior cloning baseline, outside the simulator."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import numpy as np

from excavation_sim.core import JointCommand
from excavation_sim.episodes import load_episode
from excavation_sim.packed import iter_records
from excavation_sim.provenance import environment_info, source_identity
from excavation_sim.scenarios import load_suite

FEATURE_SCHEMA = "joint-reactive-v1:time,position3,velocity3,force3,joint_position4,joint_velocity4"


def features(observation):
    if not isinstance(observation, dict):
        observation = asdict(observation)
    values = [
        observation["time_s"],
        *observation["tool_position_m"],
        *observation["tool_velocity_m_s"],
        *observation["soil_force_n"],
        *observation["joint_position_rad"],
        *observation["joint_velocity_rad_s"],
    ]
    result = np.asarray(values, dtype=np.float64)
    if result.shape != (18,) or not np.isfinite(result).all():
        raise ValueError("expected finite articulated-machine observations")
    return result


class ClonedPolicy:
    def __init__(self, checkpoint):
        self.checkpoint = Path(checkpoint)
        with np.load(self.checkpoint, allow_pickle=False) as data:
            if str(data["feature_schema"]) != FEATURE_SCHEMA:
                raise ValueError("unsupported feature schema")
            self.mean, self.scale, self.weights = data["mean"], data["scale"], data["weights"]
        if self.mean.shape != (18,) or self.scale.shape != (18,) or self.weights.shape != (19, 4):
            raise ValueError("invalid checkpoint dimensions")
        if (
            not all(np.isfinite(a).all() for a in (self.mean, self.scale, self.weights))
            or (self.scale <= 0).any()
        ):
            raise ValueError("invalid checkpoint values")

    def reset(self, seed):
        self.seed = seed

    def act(self, observation):
        if not observation.sensor_valid:
            return JointCommand((0.0, 0.0, 0.0, 0.0))
        x = np.append((features(observation) - self.mean) / self.scale, 1.0)
        return JointCommand(tuple(map(float, np.clip(x @ self.weights, -1.0, 1.0))))


def train(episodes, output, ridge, suite_path=None):
    if not np.isfinite(ridge) or ridge <= 0:
        raise ValueError("ridge must be finite and positive")
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    xs, ys, inputs = [], [], []
    seen = set()
    seen_transitions = set()
    suite = load_suite(suite_path) if suite_path else None
    for directory in episodes:
        directory = directory.resolve()
        if directory in seen:
            raise ValueError("duplicate training episode")
        seen.add(directory)
        packed = (directory / "index.json").exists()
        if packed:
            path = directory / "index.json"
            index = json.loads(path.read_text())
            manifest = index["source_manifest"]
            transition_hash = index["source_transitions_sha256"]
            rows = ((row["observation"], row["command"]) for row in iter_records(directory))
        else:
            outcome = json.loads((directory / "outcome.json").read_text())
            if outcome["status"] != "completed":
                raise ValueError("failed or interrupted simulation cannot supply demonstrations")
            path = directory / "transitions.jsonl"
            transition_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = json.loads((directory / "manifest.json").read_text())
            rows = ((row.observation, asdict(row.command)) for row in load_episode(directory))
        if suite:
            config = manifest["config"]
            if (
                config.get("split") != "train"
                or config.get("suite_sha256") != suite["sha256"]
                or config.get("scenario") not in suite["splits"]["train"]
            ):
                raise ValueError("demonstration is not in the frozen training split")
        raw = path.read_bytes()
        if transition_hash in seen_transitions:
            raise ValueError("duplicate transition data in training inputs")
        seen_transitions.add(transition_hash)
        count = 0
        for observation, command in rows:
            xs.append(features(observation))
            if set(command) != {"velocity_targets"}:
                raise ValueError("baseline requires joint velocity demonstrations")
            y = np.asarray(command["velocity_targets"], dtype=np.float64)
            if y.shape != (4,) or not np.isfinite(y).all() or (abs(y) > 1).any():
                raise ValueError("invalid demonstration command")
            ys.append(y)
            count += 1
        inputs.append(
            {
                "episode": str(directory),
                "transitions": count,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "transitions_sha256": transition_hash,
            }
        )
    if not xs:
        raise ValueError("no demonstrations")
    x, y = np.asarray(xs), np.asarray(ys)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale = np.maximum(scale, 1e-6)
    design = np.column_stack(((x - mean) / scale, np.ones(len(x))))
    penalty = np.eye(design.shape[1]) * ridge
    penalty[-1, -1] = 0
    weights = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    np.savez(
        output / "policy.npz",
        mean=mean,
        scale=scale,
        weights=weights,
        feature_schema=np.array(FEATURE_SCHEMA),
    )
    report = {
        "method": "linear ridge behavior cloning",
        "feature_schema": FEATURE_SCHEMA,
        "ridge": ridge,
        "suite_sha256": suite["sha256"] if suite else None,
        "training_inputs": inputs,
        "training_transitions": len(x),
        "training_command_rmse": float(np.sqrt(((design @ weights - y) ** 2).mean())),
        "wall_time_s": perf_counter() - started,
        "source": source_identity(Path.cwd()),
        "environment": environment_info(),
        "claims": "Training fit only; independent closed-loop evaluation required. "
        "Completed episodes may contain task failures.",
    }
    (output / "training.json").write_text(json.dumps(report, indent=2))
    (output / "policy-kwargs.json").write_text(
        json.dumps({"checkpoint": str((output / "policy.npz").resolve())})
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episodes", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ridge", type=float, default=1.0)
    parser.add_argument("--suite", type=Path)
    args = parser.parse_args()
    print(json.dumps(train(args.episodes, args.output, args.ridge, args.suite), indent=2))
