"""Record repeatable software checks without promoting any physical validation gate."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from excavation_sim.provenance import environment_info, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    before = source_identity(root)
    commands = []

    def run(command):
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        commands.append(dict(command=command, exit_code=result.returncode,
                             stdout=result.stdout, stderr=result.stderr))
        print(f"{command[2]}: exit {result.returncode}", flush=True)
        return result.returncode == 0

    for command in (
        [sys.executable, "-m", "ruff", "check", "src", "scripts", "tests", "experiments"],
        [sys.executable, "-m", "pytest", "-q"],
        [sys.executable, "-m", "build", "--no-isolation", "--outdir",
         str(args.output.resolve() / "dist")],
    ):
        run(command)
    wheels = list((args.output / "dist").glob("*.whl"))
    if commands[-1]["exit_code"] == 0 and len(wheels) == 1:
        environment = args.output.resolve() / "clean-install"
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if run([sys.executable, "-m", "venv", str(environment)]):
            if run([str(python), "-m", "pip", "install", "--no-index", "--no-deps",
                    str(wheels[0].resolve())]):
                run([str(python), "-I", "-c",
                     "from importlib.resources import files; "
                     "import excavation_sim; from excavation_sim.cli import main; "
                     "assert files('excavation_sim').joinpath('inspection.html').is_file(); "
                     "assert files('excavation_sim').joinpath('live.js').is_file(); "
                     "print(excavation_sim.__file__)"])
    after = source_identity(root)
    report = {
        "scope": "CPU contracts, lint, build, clean base-package install and viewer assets; "
                 "excludes optional physics dependencies and GPU integration",
        "source": before,
        "source_changed_during_check": before["source_sha256"] != after["source_sha256"],
        "environment": environment_info(),
        "commands": commands,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return int(report["source_changed_during_check"] or any(c["exit_code"] for c in commands))


if __name__ == "__main__":
    raise SystemExit(main())
