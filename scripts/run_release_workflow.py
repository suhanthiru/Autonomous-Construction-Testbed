"""Run the scenario-to-report reference workflow with a frozen source tree and retained failures."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from excavation_sim.provenance import environment_info, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--actions", type=int, default=1350)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path.cwd()
    identity = source_identity(root)
    python = sys.executable
    training = args.output / "demonstration"
    dataset = args.output / "dataset"
    checkpoint = args.output / "baseline"
    suite = "scenarios/v1/suite.json"
    commands = [
        ("hardware", [python, "-m", "excavation_sim.cli", "doctor"]),
        (
            "demonstration",
            [
                python,
                "scripts/run_tool_episode.py",
                "--suite",
                suite,
                "--scenario",
                "flat-reference",
                "--policy",
                "experiments/excavator_edge_cut.py",
                "--policy-class",
                "ExcavatorPolicy",
                "--actions",
                str(args.actions),
                "--task",
                "deposit",
                "--inspect",
                "--output",
                str(training),
            ],
        ),
        ("dataset", [python, "scripts/export_dataset.py", str(training), "--output", str(dataset)]),
        (
            "training",
            [
                python,
                "experiments/behavior_cloning.py",
                str(dataset),
                "--suite",
                suite,
                "--output",
                str(checkpoint),
            ],
        ),
        (
            "scripted",
            [
                python,
                "scripts/evaluate_suite.py",
                "--suite",
                suite,
                "--split",
                "test",
                "--policy",
                "experiments/excavator_edge_cut.py",
                "--policy-class",
                "ExcavatorPolicy",
                "--actions",
                str(args.actions),
                "--output",
                str(args.output / "scripted"),
            ],
        ),
        (
            "baseline",
            [
                python,
                "scripts/evaluate_suite.py",
                "--suite",
                suite,
                "--split",
                "test",
                "--policy",
                "experiments/behavior_cloning.py",
                "--policy-class",
                "ClonedPolicy",
                "--policy-kwargs",
                str(checkpoint / "policy-kwargs.json"),
                "--actions",
                str(args.actions),
                "--output",
                str(args.output / "baseline-test"),
            ],
        ),
    ]
    results = []
    for name, command in commands:
        if source_identity(root)["source_sha256"] != identity["source_sha256"]:
            raise RuntimeError("source changed; preserve this run and start a new frozen workflow")
        started = perf_counter()
        with (args.output / (name + ".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        results.append(
            {
                "stage": name,
                "command": command,
                "exit_code": result.returncode,
                "wall_time_s": perf_counter() - started,
            }
        )
        report = {
            "source": identity,
            "environment": environment_info(),
            "stages": results,
            "source_changed": source_identity(root)["source_sha256"] != identity["source_sha256"],
            "claims": "Executed workflow; task failures and physical gates remain separate.",
        }
        (args.output / "workflow.json").write_text(json.dumps(report, indent=2))
        print(f"{name}: exit {result.returncode}", flush=True)
        if result.returncode:
            return result.returncode
    return int(report["source_changed"])


if __name__ == "__main__":
    raise SystemExit(main())
