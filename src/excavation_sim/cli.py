import argparse
import json
import shutil
import subprocess
from pathlib import Path

from excavation_sim.provenance import environment_info


def doctor() -> dict:
    report = environment_info()
    executable = shutil.which("nvidia-smi")
    if executable:
        result = subprocess.run(
            [executable, "--query-gpu=name,memory.total,driver_version", "--format=csv"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        report["gpu"] = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    else:
        report["gpu"] = "nvidia-smi unavailable"
    report["physical_validation"] = "not assessed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Excavation research testbed")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("doctor", help="show runtime and hardware without starting physics")
    subcommands.add_parser(
        "validation-status", help="report coverage; exit nonzero until all required gates pass"
    )
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps(doctor(), indent=2))
    elif args.command == "validation-status":
        from excavation_sim.validation import coverage_status

        root = Path.cwd()
        manifest = json.loads((root / "validation/coverage.json").read_text(encoding="utf-8"))
        report = coverage_status(root, manifest)
        print(json.dumps(report, indent=2))
        return 0 if report["validation_complete"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
