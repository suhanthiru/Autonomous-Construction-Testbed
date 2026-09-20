"""Compare inner iteration caps without changing the prepared fixture."""

import gzip
import importlib.util
import json
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    folder = Path(__file__).resolve().parent
    prep = load_module("prep", folder.parent / "contact-fixed-preparation/reproduce.py")
    inputs = load_module("inputs", folder.parent / "contact-grid-only/reproduce.py")
    study = json.loads((folder / "study.json").read_text())
    records, audits = [], []
    for root, name in ((folder.parent / "contact-grid-only", "grid10mm-summary.json"),
                       (folder, "cap500k-summary.json")):
        summary = json.loads((root / name).read_text())
        audits.append(prep.audit_record(root, summary))
        records.append(json.loads(gzip.decompress((root / summary["file"]).read_bytes())))
    inputs.check_fixed_inputs(*records, study["source_sha256"])
    a, b = records
    if a["mpm"].keys() != b["mpm"].keys():
        raise ValueError("MPM configuration fields differ")
    differences = {k: [v, b["mpm"][k]] for k, v in a["mpm"].items() if v != b["mpm"][k]}
    if differences != {"iterations": [200000, 500000]}:
        raise ValueError(f"Unexpected configuration differences: {differences}")
    for key in ("dt_s", "world_offset_m"):
        if a[key] != b[key]:
            raise ValueError(f"Uncontrolled difference: {key}")
    for key in ("preparation_dt_s", "preparation_duration_s", "state_fingerprints"):
        if audits[0][key] != audits[1][key]:
            raise ValueError(f"Prepared fixture differs: {key}")
    if len(audits[0]["state_fingerprints"]) != 9:
        raise ValueError("Missing prepared-state fingerprints")
    print(json.dumps(dict(
        baseline=audits[0], higher_cap=audits[1], configuration_differences=differences,
        impulse_change_fraction=b["total_vertical_impulse_n_s"] /
        a["total_vertical_impulse_n_s"] - 1,
        peak_change_fraction=b["peak_20ms_mean_n"] / a["peak_20ms_mean_n"] - 1,
        higher_cap_inner_passed=(audits[1]["preparation_inner_passed"] and
                                 audits[1]["digging"]["solver_health"]["passed"]),
        evidence_integrity_passed=True, physical_validation=False,
    ), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
