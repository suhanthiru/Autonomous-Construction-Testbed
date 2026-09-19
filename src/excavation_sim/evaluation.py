"""Evaluator-only summaries from retained episodes; policy inputs are never extended."""

import json
import math
from pathlib import Path


def summarize_episode(directory: Path, load_limit_n: float = 100.0) -> dict:
    if not math.isfinite(load_limit_n) or load_limit_n <= 0:
        raise ValueError("load limit must be finite and positive")
    manifest = json.loads((directory / "manifest.json").read_text())
    outcome_path = directory / "outcome.json"
    outcome = (
        json.loads(outcome_path.read_text())
        if outcome_path.exists()
        else {"status": "interrupted", "reason": "no outcome record"}
    )
    evaluation = [
        json.loads(line) for line in (directory / "evaluation.jsonl").read_text().splitlines()
    ]
    transitions = [
        json.loads(line) for line in (directory / "transitions.jsonl").read_text().splitlines()
    ]
    if len(evaluation) != len(transitions):
        raise ValueError("evaluation and transition streams disagree")
    peak, impulse, over_limit_time, escaped, lifted = 0.0, 0.0, 0.0, 0.0, 0.0
    for row, transition in zip(evaluation, transitions, strict=True):
        if row["tick"] != transition["next_observation"]["tick"]:
            raise ValueError("evaluation ticks disagree with transitions")
        # Evaluation of raw force is preserved separately by rollout when sensors are noisy.
        force = row.get("raw_soil_force_n", transition["next_observation"]["soil_force_n"])
        norm = math.sqrt(sum(v * v for v in force))
        duration = transition["duration_s"]
        peak = max(peak, norm)
        impulse += norm * duration
        over_limit_time += duration if norm > load_limit_n else 0
        d = row["diagnostics"]
        escaped = max(escaped, d["escaped_mass_kg"])
        lifted = max(lifted, d.get("lifted_bucket_mass_kg") or 0.0)
    final = evaluation[-1] if evaluation else {}
    diagnostics = final.get("diagnostics", {})
    task = final.get("task") or {}
    time_s = transitions[-1]["next_observation"]["time_s"] if transitions else 0.0
    deposited = diagnostics.get("deposited_mass_kg") or 0.0
    performance_path = directory / "performance.json"
    performance = json.loads(performance_path.read_text()) if performance_path.exists() else {}
    return {
        "episode": str(directory),
        "scenario": manifest.get("config", {}).get("scenario"),
        "status": outcome["status"],
        "reason": outcome.get("reason"),
        "task_success": bool(task.get("success", False)) and outcome["status"] == "completed",
        "simulated_time_s": time_s,
        "wall_time_s": performance.get("wall_time_s"),
        "source_changed": performance.get("source_changed"),
        "deposited_mass_kg": deposited,
        "peak_lifted_mass_kg": lifted,
        "productivity_kg_s": deposited / time_s if time_s else 0,
        "positive_actuator_work_j": diagnostics.get("positive_actuator_work_j"),
        "peak_load_n": peak,
        "load_norm_integral_n_s": impulse,
        "load_limit_n": load_limit_n,
        "time_over_load_limit_s": over_limit_time,
        "escaped_mass_kg": escaped,
        "load_definition": "action-averaged generated soil-force norm; threshold is an "
        "evaluation budget, not a validated safe machine limit",
        "force_access": "raw"
        if all("raw_soil_force_n" in r for r in evaluation)
        else "recorded observation (may include sensor effects)",
    }
