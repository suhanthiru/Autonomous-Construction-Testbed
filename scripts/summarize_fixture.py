"""Summarize fixture records without importing the physics engine."""

import argparse
import json
from pathlib import Path

from excavation_sim.analysis import windowed_force
from excavation_sim.provenance import fingerprint


def summarize(path: Path) -> dict:
    raw = path.read_bytes()
    run = json.loads(raw)
    rows = run["trajectory"]
    dt = run["dt_s"]
    return {
        "file": path.name,
        "canonical_json_sha256": fingerprint(run),
        "source_sha256": run["source"]["source_sha256"],
        "dt_s": dt,
        "control_dt_s": run.get("control_dt_s", dt),
        "peak_20ms_mean_soil_force_z_n": max(
            windowed_force([row["soil_impulse_n_s"][2] for row in rows], dt, 0.02)
        ),
        "measurement_window_s": 0.02,
        "duration_s": rows[-1]["time_s"],
        "with_soil": run["with_soil"],
        "final_z_m": rows[-1]["body_z_m"],
        "minimum_z_m": min(row["body_z_m"] for row in rows),
        "peak_abs_actuator_force_n": max(abs(row["actuator_force_z_n"]) for row in rows),
        "peak_soil_force_z_n": max(row["soil_force_z_n"] for row in rows),
        "integrated_soil_impulse_z_n_s": sum(row["soil_impulse_n_s"][2] for row in rows),
        "actuator_work_z_j": sum(
            row["actuator_force_z_n"] * (row["body_z_m"] - previous_z)
            for row, previous_z in zip(
                rows, [run["initial_body_z_m"]] + [r["body_z_m"] for r in rows[:-1]], strict=True
            )
        ),
        "work_definition": "vertical force held over each step times vertical displacement",
        "status": "diagnostic only; no convergence or physical validation verdict",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps([summarize(path) for path in args.records], indent=2, allow_nan=False))
