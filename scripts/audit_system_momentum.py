"""Vertical body/soil/ground momentum ledger for the single-tool fixture."""

import argparse
import json
from math import fsum
from pathlib import Path

from excavation_sim.provenance import fingerprint


def residual_summary(values: list[float]) -> dict:
    return {
        "max_abs_step_n_s": max(abs(value) for value in values),
        "signed_total_n_s": fsum(values),
        "sum_abs_step_n_s": fsum(abs(value) for value in values),
    }


def audit(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    dt = record["dt_s"]
    mass = record["body_mass_kg"]
    soil_mass = record["initial_soil_mass_kg"]
    previous_soil = record["initial_soil_momentum_kg_m_s"][2]
    previous_body = 0.0
    soil_residuals, system_residuals, corrected_residuals, ledger = [], [], [], []
    for row in record["trajectory"]:
        body = mass * row["body_vz_m_s"]
        soil = row["soil_momentum_kg_m_s"][2]
        tool_impulse = row["soil_impulse_n_s"][2]
        ground_impulse = row["impulse_on_ground_n_s"][2]
        # Collider impulses act on the collider, with the opposite sign on soil.
        soil_residuals.append(
            soil - previous_soil + soil_mass * 9.81 * dt + tool_impulse + ground_impulse
        )
        external = (row["actuator_force_z_n"] - (mass + soil_mass) * 9.81) * dt - ground_impulse
        system_residual = body - previous_body + soil - previous_soil - external
        feedback_gap = row["applied_contact_impulse_z_n_s"] - tool_impulse
        system_residuals.append(system_residual)
        corrected_residuals.append(system_residual - feedback_gap)
        ledger.append(
            {
                "tick": row["tick"],
                "soil_residual_n_s": soil_residuals[-1],
                "system_residual_n_s": system_residual,
                "applied_minus_generated_n_s": feedback_gap,
                "residual_after_feedback_gap_n_s": corrected_residuals[-1],
            }
        )
        previous_soil, previous_body = soil, body
    return {
        "file": path.name,
        "canonical_json_sha256": fingerprint(record),
        "soil_residual": residual_summary(soil_residuals),
        "system_residual": residual_summary(system_residuals),
        "system_residual_after_feedback_gap": residual_summary(corrected_residuals),
        "ledger": ledger,
        "status": "diagnostic; subtracting feedback gap is attribution, not a conservation pass",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps([audit(path) for path in args.records], indent=2, allow_nan=False))
