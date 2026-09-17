"""Audit recorded vertical rigid-body momentum without running the physics engine."""

import argparse
import json
from pathlib import Path

from excavation_sim.analysis import vertical_momentum_audit
from excavation_sim.provenance import fingerprint


def audit(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    rows = record["trajectory"]
    result = {
        "file": path.name,
        "canonical_json_sha256": fingerprint(record),
        "dt_s": record["dt_s"],
        "assumptions": "initial vz=0; gravity=9.81; other contacts appear in residual",
        "audit": vertical_momentum_audit(
            [row["body_vz_m_s"] for row in rows],
            [row["actuator_force_z_n"] for row in rows],
            [row["soil_impulse_n_s"][2] for row in rows],
            mass_kg=record["body_mass_kg"],
            dt_s=record["dt_s"],
        ),
    }
    if all("applied_contact_impulse_z_n_s" in row for row in rows):
        result["applied_force_audit"] = vertical_momentum_audit(
            [row["body_vz_m_s"] for row in rows],
            [row["actuator_force_z_n"] for row in rows],
            [row["applied_contact_impulse_z_n_s"] for row in rows],
            mass_kg=record["body_mass_kg"],
            dt_s=record["dt_s"],
        )["same_step"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([audit(path) for path in args.records], indent=2, allow_nan=False))
