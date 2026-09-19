"""Execute frozen scenarios with an external policy and regenerate an evidence-based report."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from excavation_sim.evaluation import summarize_episode
from excavation_sim.provenance import environment_info, fingerprint, source_identity
from excavation_sim.scenarios import load_suite


def render_report(directory, results):
    lines = [
        "# Scenario evaluation",
        "",
        "Development physics; no physical validation claim.",
        "",
        "| Scenario | Status | Success | Deposit kg | Peak load N | Work J | Wall s |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['scenario_name']} | {row['status']} | {row['task_success']} | "
            f"{row['deposited_mass_kg']:.4f} | {row['peak_load_n']:.2f} | "
            f"{row.get('positive_actuator_work_j')} | {row['process_wall_time_s']:.2f} |"
        )
    lines += [
        "",
        "All attempted episodes remain in the denominator. One checkpoint is one training",
        "run; scenario variation is not independent training replication. These small suites",
        "report per-condition outcomes and ranges, not an inferential performance claim.",
        "",
        "The load threshold is an evaluation budget, not a validated machine safety limit.",
    ]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    labels = [r["scenario_name"] for r in results]
    axes[0].bar(labels, [r["deposited_mass_kg"] for r in results])
    axes[0].axhline(0.5, color="red", linestyle="--", label="Task goal")
    axes[0].set_ylabel("Deposited mass (kg)")
    axes[0].legend()
    axes[1].bar(labels, [r["peak_load_n"] for r in results])
    axes[1].set_ylabel("Peak action-averaged load (N)")
    for axis in axes:
        axis.tick_params(axis="x", labelrotation=20)
    fig.suptitle("Recorded outcomes — development physics")
    fig.savefig(directory / "outcomes.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=Path("scenarios/v1/suite.json"))
    parser.add_argument("--split", choices=["train", "development", "test"], default="test")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-class", required=True)
    parser.add_argument("--policy-kwargs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--actions", type=int, default=1350)
    parser.add_argument(
        "--world-config", type=Path, default=Path("configs/machine-development.json")
    )
    parser.add_argument("--sensor-config", type=Path)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.report_only:
        report = json.loads((args.output / "results.json").read_text())
        render_report(args.output, report["results"])
        return 0
    if args.actions < 1:
        raise ValueError("positive action budget required")
    suite = load_suite(args.suite)
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_identity(Path.cwd())
    artifacts = [args.policy, args.suite, args.world_config]
    if args.policy_kwargs:
        artifacts.append(args.policy_kwargs)
        kwargs = json.loads(args.policy_kwargs.read_text())
        if "checkpoint" in kwargs:
            artifacts.append(Path(kwargs["checkpoint"]))
    if args.sensor_config:
        artifacts.append(args.sensor_config)
    manifest = {
        "source": source,
        "environment": environment_info(),
        "split": args.split,
        "actions_per_episode": args.actions,
        "suite_sha256": suite["sha256"],
        "artifacts": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    results = []
    for scenario in suite["splits"][args.split]:
        directory = args.output / scenario["name"]
        command = [
            sys.executable,
            "scripts/run_tool_episode.py",
            "--suite",
            str(args.suite),
            "--scenario",
            scenario["name"],
            "--policy",
            str(args.policy),
            "--policy-class",
            args.policy_class,
            "--world-config",
            str(args.world_config),
            "--actions",
            str(args.actions),
            "--task",
            "deposit",
            "--inspect",
            "--output",
            str(directory),
        ]
        if args.policy_kwargs:
            command += ["--policy-kwargs", str(args.policy_kwargs)]
        if args.sensor_config:
            command += ["--sensor-config", str(args.sensor_config)]
        started = perf_counter()
        with (args.output / (scenario["name"] + ".log")).open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        elapsed = perf_counter() - started
        if (directory / "manifest.json").exists():
            result = summarize_episode(directory)
        else:
            result = {
                "status": "failed",
                "reason": "failed before recording began",
                "task_success": False,
                "deposited_mass_kg": 0.0,
                "peak_load_n": 0.0,
            }
        result.update(
            scenario_name=scenario["name"],
            process_exit_code=process.returncode,
            process_wall_time_s=elapsed,
        )
        results.append(result)
        report = {
            "manifest_sha256": fingerprint(manifest),
            "results": results,
            "source_changed": source["source_sha256"]
            != source_identity(Path.cwd())["source_sha256"],
        }
        (args.output / "results.json").write_text(json.dumps(report, indent=2))
        print(
            f"{scenario['name']}: {result['status']}, success={result['task_success']}", flush=True
        )
    render_report(args.output, results)
    return int(any(row["process_exit_code"] for row in results) or report["source_changed"])


if __name__ == "__main__":
    raise SystemExit(main())
