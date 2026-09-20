"""Audit timestep comparisons with recorded preparation-state fingerprints."""

import importlib.util
import json
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "preparation_audit", folder.parent / "contact-fixed-preparation/reproduce.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    cases = []
    expected_arrays = {"particle_q", "particle_qd", "body_q", "body_qd",
                       "mpm.particle_elastic_strain", "mpm.particle_transform",
                       "mpm.particle_qd_grad", "mpm.particle_stress", "mpm.particle_Jp"}
    for dt in (0.0025, 0.00125, 0.000625):
        summary = json.loads((folder / f"dt-{dt}-summary.json").read_text())
        row = audit.audit_record(folder, summary)
        if row["digging"]["dt_s"] != dt or set(row["state_fingerprints"]) != expected_arrays:
            raise ValueError("Unexpected timestep or incomplete preparation fingerprints")
        if cases:
            for key in ("state_fingerprints", "preparation_dt_s", "preparation_duration_s"):
                if row[key] != cases[0][key]:
                    raise ValueError(f"Uncontrolled preparation difference: {key}")
            for key in ("mpm", "world_offset_m", "source_sha256"):
                if row["digging"][key] != cases[0]["digging"][key]:
                    raise ValueError(f"Uncontrolled configuration difference: {key}")
        cases.append(row)
    changes = []
    for a, b in zip(cases[:-1], cases[1:], strict=True):
        a, b = a["digging"], b["digging"]
        changes.append(dict(coarse_dt_s=a["dt_s"], fine_dt_s=b["dt_s"],
                            impulse_change_fraction=b["impulse_n_s"] / a["impulse_n_s"] - 1,
                            peak_change_fraction=b["peak_20ms_mean_n"] / a["peak_20ms_mean_n"] - 1))
    print(json.dumps(dict(cases=cases, changes=changes, evidence_integrity_passed=True,
                          recorded_prepared_arrays_match=True,
                          all_inner_checks_passed=all(r["preparation_inner_passed"] and
                                                      r["digging"]["solver_health"]["passed"]
                                                      for r in cases),
                          physical_validation=False), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
