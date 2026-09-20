"""Audit all Q1 timestep cases using the retained, checksum-verified records."""

import importlib.util
import json
import math
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "contact_audit", folder.parent / "contact-spatial-refinement/reproduce.py"
    )
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    cases = []
    for dt, name in [(0.0025, "q1-0.0025-summary.json"),
                     (0.00125, "q1-summary.json"),
                     (0.000625, "q1-0.000625-summary.json")]:
        row = audit.audit(folder, json.loads((folder / name).read_text()))
        audit.require(math.isclose(row["dt_s"], dt), "Unexpected timestep")
        audit.require(row["mpm"]["collider_basis"] == "Q1", "Unexpected contact basis")
        if cases:
            for key in ("mpm", "world_offset_m", "source_sha256"):
                audit.require(row[key] == cases[0][key], f"Uncontrolled difference: {key}")
        cases.append(row)
    changes = [dict(coarse_dt_s=a["dt_s"], fine_dt_s=b["dt_s"],
                    impulse_change_fraction=b["impulse_n_s"] / a["impulse_n_s"] - 1,
                    peak_change_fraction=b["peak_20ms_mean_n"] / a["peak_20ms_mean_n"] - 1)
               for a, b in zip(cases[:-1], cases[1:], strict=True)]
    print(json.dumps(dict(cases=cases, changes=changes, evidence_integrity_passed=True,
                          all_inner_checks_passed=all(r["solver_health"]["passed"] for r in cases),
                          physical_validation=False), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
