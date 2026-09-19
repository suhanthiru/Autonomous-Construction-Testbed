"""Repeat the existing controlled penetration fixture with additional proxy relaxation."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from check_soil_coupling import run

from excavation_sim.provenance import source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--mode", choices=["lagged", "staggered"], default="lagged")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_identity(Path.cwd())
    results = []
    for dt in (0.005, 0.0025, 0.00125):
        started = perf_counter()
        name = f"dt-{dt}"
        try:
            record = run(
                round(1.2 / dt),
                dt,
                drive=True,
                control_dt=0.005,
                coupling_iterations=args.iterations,
                mpm_iterations=100,
                mpm_tolerance=1e-5,
                proxy_mode=args.mode,
            )
            (args.output / (name + ".json")).write_text(json.dumps(record, indent=2))
            status, error = "completed", None
        except Exception as failure:
            status, error = "failed", f"{type(failure).__name__}: {failure}"
        results.append(
            {"dt_s": dt, "status": status, "error": error, "wall_time_s": perf_counter() - started}
        )
        (args.output / "execution.json").write_text(
            json.dumps(
                {
                    "source": source,
                    "source_changed": source["source_sha256"]
                    != source_identity(Path.cwd())["source_sha256"],
                    "cases": results,
                    "claim": "Sensitivity check; completion is not an acceptance pass",
                },
                indent=2,
            )
        )
        print(f"{name}: {status}", flush=True)


if __name__ == "__main__":
    main()
