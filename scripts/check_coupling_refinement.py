"""Repeat the existing controlled penetration fixture with additional proxy relaxation."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from check_soil_coupling import run

from excavation_sim.actuation import ticks_per_update
from excavation_sim.provenance import source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--mode", choices=["lagged", "staggered"], default="lagged")
    parser.add_argument("--dt", type=float, nargs="+", default=[0.005, 0.0025, 0.00125])
    parser.add_argument("--proxy-relaxation", type=float, default=1.0)
    parser.add_argument("--relaxation-mode", choices=["fixed", "aitken"], default="fixed")
    args = parser.parse_args()
    try:
        if args.iterations < 1 or len(set(args.dt)) != len(args.dt):
            raise ValueError("positive iterations and distinct timesteps required")
        for dt in args.dt:
            for period in (0.005, 0.02, 1.2):
                ticks_per_update(dt, period)
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_identity(Path.cwd())
    results = []
    for dt in args.dt:
        started = perf_counter()
        name = f"dt-{dt}"
        try:
            record = run(
                ticks_per_update(dt, 1.2),
                dt,
                drive=True,
                control_dt=0.005,
                coupling_iterations=args.iterations,
                mpm_iterations=100,
                mpm_tolerance=1e-5,
                proxy_mode=args.mode,
                proxy_relaxation=args.proxy_relaxation,
                relaxation_mode=args.relaxation_mode,
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
    return int(
        any(case["status"] != "completed" for case in results)
        or source["source_sha256"] != source_identity(Path.cwd())["source_sha256"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
