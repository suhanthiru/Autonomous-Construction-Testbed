"""Audit grid refinement while holding particles and timesteps fixed."""

import gzip
import importlib.util
import json
import math
from pathlib import Path


def check_fixed_inputs(left, right, expected_source):
    for record in (left, right):
        if record["source"]["source_sha256"] != expected_source:
            raise ValueError("Unexpected fixture source")
    for key in ("boundary", "duration_s", "zero_initial_stress_delta", "environment"):
        if left[key] != right[key]:
            raise ValueError(f"Uncontrolled fixture/runtime difference: {key}")
    for key in ("gravity_m_s2", "particle_mass_kg"):
        if left["momentum_accounting"][key] != right["momentum_accounting"][key]:
            raise ValueError(f"Uncontrolled physical input: {key}")
    if len(left["trajectory"]) != len(right["trajectory"]):
        raise ValueError("Prescribed motion length differs")
    for a, b in zip(left["trajectory"], right["trajectory"], strict=True):
        if any(a[key] != b[key] for key in ("time_s", "input_vz_m_s")):
            raise ValueError("Prescribed motion timing or velocity differs")
        # Commands contain global z, including the declared fixture translation.
        za = a["input_z_m"] - left["world_offset_m"][2]
        zb = b["input_z_m"] - right["world_offset_m"][2]
        if not math.isclose(za, zb, rel_tol=0, abs_tol=1e-14):
            raise ValueError("Prescribed motion relative to ground differs")


def main():
    folder = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "prep_audit", folder.parent / "contact-fixed-preparation/reproduce.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    baseline_folder = folder.parent / "contact-particle-resolution"
    baseline = audit.audit_record(baseline_folder, json.loads(
        (baseline_folder / "particles5mm-summary.json").read_text()))
    fine = audit.audit_record(folder, json.loads((folder / "grid10mm-summary.json").read_text()))
    study = json.loads((folder / "study.json").read_text())
    raw = []
    for root, name in ((baseline_folder, "particles5mm-summary.json"),
                       (folder, "grid10mm-summary.json")):
        summary = json.loads((root / name).read_text())
        raw.append(json.loads(gzip.decompress((root / summary["file"]).read_bytes())))
    check_fixed_inputs(*raw, study["source_sha256"])
    a, b = baseline["digging"], fine["digging"]
    if a["mpm"].keys() != b["mpm"].keys():
        raise ValueError("Configuration fields differ")
    differences = {k: [v, b["mpm"][k]] for k, v in a["mpm"].items() if v != b["mpm"][k]}
    if differences != {"voxel_m": [0.02, 0.01]}:
        raise ValueError(f"Unexpected grid-control differences: {differences}")
    for row in (a, b):
        if row["world_offset_m"] != [row["mpm"]["voxel_m"] / 2] * 3:
            raise ValueError("Unexpected fixture alignment")
    for key in ("dt_s", "source_sha256"):
        if a[key] != b[key]:
            raise ValueError(f"Uncontrolled difference: {key}")
    for key in ("preparation_dt_s", "preparation_duration_s"):
        if baseline[key] != fine[key]:
            raise ValueError(f"Preparation setting differs: {key}")
    print(json.dumps(dict(
        baseline=baseline, fine=fine, configuration_differences=differences,
        impulse_change_fraction=b["impulse_n_s"] / a["impulse_n_s"] - 1,
        peak_change_fraction=b["peak_20ms_mean_n"] / a["peak_20ms_mean_n"] - 1,
        evidence_integrity_passed=True,
        recorded_motion_and_physical_inputs_match=True,
        all_inner_checks_passed=all(r["preparation_inner_passed"] and
                                   r["digging"]["solver_health"]["passed"]
                                   for r in (baseline, fine)),
        physical_validation=False,
        limitation=("Grid and whole-fixture half-cell translation change; "
                    "prepared states may differ"),
    ), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
