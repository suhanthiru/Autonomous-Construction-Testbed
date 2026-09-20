"""Recompute momentum accounting without importing the simulator."""

import gzip
import importlib.util
import json
import math
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "contact_audit", folder.parent / "contact-spatial-refinement/reproduce.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary = json.loads((folder / "q1-summary.json").read_text())
    audited = module.audit(folder, summary)
    data = json.loads(gzip.decompress((folder / summary["file"]).read_bytes()))
    meta = data["momentum_accounting"]
    previous = meta["initial_particle_momentum_kg_m_s"]
    residuals = []
    unassigned = []
    for row in data["trajectory"]:
        momentum = row["particle_momentum_kg_m_s"]
        for axis in range(3):
            change = momentum[axis] - previous[axis]
            gravity = meta["particle_mass_kg"] * meta["gravity_m_s2"][axis] * data["dt_s"]
            expected = {
                "particle_momentum_change_n_s": change,
                "gravity_impulse_n_s": gravity,
                "unaccounted_momentum_n_s": (
                    change - gravity + row["all_collider_reaction_n_s"][axis]),
            }
            for key, value in expected.items():
                module.require(math.isfinite(value) and math.isclose(
                    value, row[key][axis], rel_tol=1e-12, abs_tol=1e-12),
                    f"Inconsistent momentum record: {key}, {row['time_s']}")
        residuals.append(row["unaccounted_momentum_n_s"])
        unassigned.append(row["unassigned_collider_reaction_n_s"])
        previous = momentum
    baseline_path = folder.parent / "contact-basis/q1-0.00125.json.gz"
    module.audit(baseline_path.parent,
                 json.loads((baseline_path.parent / "q1-summary.json").read_text()))
    baseline = json.loads(gzip.decompress(baseline_path.read_bytes()))
    module.require(data["mpm"] == baseline["mpm"], "Baseline configuration differs")
    module.require(data["world_offset_m"] == baseline["world_offset_m"], "Alignment differs")
    module.require(data["dt_s"] == baseline["dt_s"], "Timestep differs")
    print(json.dumps(dict(
        contact_audit=audited,
        cumulative_unaccounted_n_s=[math.fsum(r[a] for r in residuals) for a in range(3)],
        sum_absolute_unaccounted_n_s=[math.fsum(abs(r[a]) for r in residuals)
                                     for a in range(3)],
        max_step_unaccounted_n_s=[max(abs(r[a]) for r in residuals) for a in range(3)],
        sum_absolute_unassigned_reaction_n_s=[math.fsum(abs(r[a]) for r in unassigned)
                                              for a in range(3)],
        tool_impulse_change_from_uninstrumented_n_s=(
            data["total_vertical_impulse_n_s"] - baseline["total_vertical_impulse_n_s"]),
        evidence_integrity_passed=True, physical_validation=False,
        limitation="Unaccounted momentum is not attributed to a particular numerical mechanism",
    ), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
