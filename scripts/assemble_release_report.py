"""Assemble a portable report from executed workflow evidence without upgrading failed gates."""

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path

from excavation_sim.provenance import source_identity
from excavation_sim.validation import coverage_status


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    workflow = read(args.workflow / "workflow.json")
    repeated = read(args.repeat / "performance.json")
    outcome = read(args.repeat / "outcome.json")
    complete_workflow = (
        len(workflow["stages"]) == 6
        and all(s["exit_code"] == 0 for s in workflow["stages"])
        and not workflow["source_changed"]
    )
    complete_repeat = (
        outcome["status"] == "completed"
        and repeated["task_result"]["success"]
        and not repeated["source_changed"]
    )
    evidence = {}

    def copy(source, relative):
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        evidence[str(relative)] = hashlib.sha256(target.read_bytes()).hexdigest()

    for name in (
        "workflow.json",
        "baseline/training.json",
        "baseline/policy.npz",
        "scripted/manifest.json",
        "scripted/results.json",
        "scripted/report.md",
        "scripted/outcomes.png",
        "baseline-test/manifest.json",
        "baseline-test/results.json",
        "baseline-test/report.md",
        "baseline-test/outcomes.png",
    ):
        copy(args.workflow / name, name)
    for name in ("manifest.json", "outcome.json", "performance.json", "runtime-model.json"):
        copy(args.repeat / name, "repeated/" + name)
    copy(args.repeat / "inspection.html", "repeated/inspection.html")
    episodes = [(args.repeat, "repeated")]
    for group in ("scripted", "baseline-test"):
        for episode in sorted((args.workflow / group).iterdir()):
            if episode.is_dir() and (episode / "manifest.json").is_file():
                relative = group + "/" + episode.name
                episodes.append((episode, relative))
                for name in ("manifest.json", "outcome.json", "performance.json"):
                    copy(episode / name, relative + "/" + name)
    for episode, relative in episodes:
        for name in ("transitions.jsonl", "evaluation.jsonl"):
            target = args.output / relative / (name + ".gz")
            target.write_bytes(gzip.compress((episode / name).read_bytes(), mtime=0))
            evidence[target.relative_to(args.output).as_posix()] = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()
    for source in (args.workflow / "dataset").iterdir():
        if source.is_file():
            copy(source, "dataset/" + source.name)
    kwargs = {"checkpoint": (args.output / "baseline/policy.npz").as_posix()}
    (args.output / "baseline/policy-kwargs.json").write_text(json.dumps(kwargs, indent=2))
    evidence["baseline/policy-kwargs.json"] = hashlib.sha256(
        (args.output / "baseline/policy-kwargs.json").read_bytes()
    ).hexdigest()
    coverage = coverage_status(Path.cwd(), read(Path("validation/coverage.json")))
    report = {
        "operational_workflow_complete": complete_workflow,
        "frozen_repeated_deposit_succeeded": complete_repeat,
        "validation_complete": coverage["validation_complete"],
        "unresolved_validation_gates": coverage["unresolved"],
        "evidence_errors": coverage["errors"],
        "frozen_source": workflow["source"],
        "report_source": source_identity(Path.cwd()),
        "evidence_sha256": evidence,
        "repeated_metrics": repeated["task_result"]["metrics"],
        "cost_context": "Other verification jobs shared the GPU during parts of execution. "
        "Recorded wall times include contention and compilation; they are not an "
        "isolated throughput comparison.",
        "claim": "Operational simulation workflow and measured outcomes. Failed numerical and "
        "physical gates remain failures; no real-machine accuracy or safety claim.",
    }
    (args.output / "release.json").write_text(json.dumps(report, indent=2))
    lines = [
        "# End-to-end system report",
        "",
        f"Frozen workflow completed: **{complete_workflow}**.",
        f"Repeated deposit task succeeded: **{complete_repeat}**.",
        f"Validation complete: **{report['validation_complete']}**.",
        "",
        "The workflow covers named scenarios, recording, compressed datasets, actual baseline",
        "training, held-out scripted/baseline evaluation and generated reports. The repeated",
        "demonstration carries soil across cuts without resetting the world.",
        "",
        "## Results",
        "",
        "See `scripted/report.md`, `baseline-test/report.md`, their figures "
        "and raw JSON summaries.",
        f"Repeated task: {repeated['task_result']['metrics']['score']:.4f} kg deposited in "
        f"{repeated['simulated_time_s']:.2f} simulated seconds.",
        "",
        "## Qualification limits",
        "",
        report["claim"],
        "",
        report["cost_context"],
        "",
        "Unresolved gates: " + ", ".join(coverage["unresolved"]) + ".",
        "",
        "This report does not label an unqualified physics model as validated. The numerical",
        "studies, physical-data comparisons, source identities and checksums remain inspectable.",
        "",
    ]
    (args.output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    if not complete_workflow or not complete_repeat or coverage["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
