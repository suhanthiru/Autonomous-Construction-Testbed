"""Recompute the fixed-grid timestep comparison from retained raw evidence."""

import importlib.util
import json
import math
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent
    shared = folder.parent / "contact-spatial-refinement"
    spec = importlib.util.spec_from_file_location("contact_audit", shared / "reproduce.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = json.loads((shared / "20mm-budget-200000-summary.json").read_text())
    study = json.loads((folder / "study.json").read_text())
    cases = [module.audit(shared, baseline)]
    baseline = cases[0]
    differences = []
    for dt in study["dt_s"]:
        summary = json.loads((folder / f"dt-{dt}-summary.json").read_text())
        result = module.audit(folder, summary)
        module.require(math.isclose(result["dt_s"], dt), "Unexpected timestep")
        module.require(result["source_sha256"] == study["expected_source_sha256"],
                       "Unexpected source snapshot")
        module.require(result["world_offset_m"] == baseline["world_offset_m"],
                       "Fixture alignment changed")
        module.require(result["mpm"].keys() == baseline["mpm"].keys(),
                       "Configuration fields differ")
        changes = {key: [value, result["mpm"].get(key)]
                   for key, value in baseline["mpm"].items()
                   if value != result["mpm"].get(key)}
        expected = {"max_active_cells": [65536, 262144],
                    "requested_warmstart": ["auto", "particles"]}
        module.require(changes == expected, f"Unexpected parameter differences: {changes}")
        differences.append(dict(dt_s=dt, differences=changes))
        cases.append(result)
    module.require(len({case["source_sha256"] for case in cases}) == 1,
                   "Source snapshots differ")
    comparisons = []
    for coarse, fine in zip(cases[:-1], cases[1:], strict=True):
        comparisons.append(dict(
            coarse_dt_s=coarse["dt_s"], fine_dt_s=fine["dt_s"],
            impulse_change_fraction=(fine["impulse_n_s"] / coarse["impulse_n_s"] - 1),
            peak_change_fraction=(fine["peak_20ms_mean_n"] / coarse["peak_20ms_mean_n"] - 1),
            both_inner_checks_passed=(coarse["solver_health"]["passed"]
                                      and fine["solver_health"]["passed"]),
        ))
    print(json.dumps(dict(cases=cases, comparisons=comparisons,
                          configuration_differences=differences,
                          evidence_integrity_passed=True, physical_validation=False),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
