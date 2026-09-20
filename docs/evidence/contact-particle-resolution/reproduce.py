"""Audit the particle-resolution control against its fixed-grid baseline."""

import importlib.util
import json
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "prep_audit", folder.parent / "contact-fixed-preparation/reproduce.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    baseline_folder = folder.parent / "contact-prepared-time"
    baseline = audit.audit_record(baseline_folder, json.loads(
        (baseline_folder / "dt-0.00125-summary.json").read_text()))
    fine = audit.audit_record(
        folder, json.loads((folder / "particles5mm-summary.json").read_text()))
    a, b = baseline["digging"], fine["digging"]
    if a["mpm"].keys() != b["mpm"].keys():
        raise ValueError("Configuration fields differ")
    differences = {k: [v, b["mpm"][k]] for k, v in a["mpm"].items() if v != b["mpm"][k]}
    if differences != {"spacing_m": [0.01, 0.005], "particle_count": [32000, 256000]}:
        raise ValueError(f"Unexpected parameter differences: {differences}")
    for key in ("dt_s", "world_offset_m", "source_sha256"):
        if a[key] != b[key]:
            raise ValueError(f"Uncontrolled difference: {key}")
    for key in ("preparation_dt_s", "preparation_duration_s"):
        if baseline[key] != fine[key]:
            raise ValueError(f"Preparation settings differ: {key}")
    print(json.dumps(dict(
        baseline=baseline, fine=fine, configuration_differences=differences,
        impulse_change_fraction=b["impulse_n_s"] / a["impulse_n_s"] - 1,
        peak_change_fraction=b["peak_20ms_mean_n"] / a["peak_20ms_mean_n"] - 1,
        evidence_integrity_passed=True,
        all_inner_checks_passed=all(r["preparation_inner_passed"] and
                                   r["digging"]["solver_health"]["passed"]
                                   for r in (baseline, fine)),
        physical_validation=False,
        limitation=("Different particle counts imply different prepared arrays; "
                    "not an identical-state test"),
    ), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
